"""
Z-AUDIT — Fraud Detection Module (v3 — Domain-Aware Scoring)
Uses Groq LLM / ChatGPT for AI-powered fraud analysis with domain-specific
knowledge about trilingual Indian field surveys.
"""

import os
import json
import re as re_mod
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Available models for fraud analysis (user selectable via dropdown)
AVAILABLE_MODELS = {
    "llama-3.3-70b-versatile": "LLaMA 3.3 70B (Best quality, slower)",
    "llama-3.1-8b-instant": "LLaMA 3.1 8B (Fast, good quality)",
    "llama3-70b-8192": "LLaMA 3 70B (High quality)",
    "llama3-8b-8192": "LLaMA 3 8B (Fastest)",
    "mixtral-8x7b-32768": "Mixtral 8x7B (Balanced)",
    "gemma2-9b-it": "Gemma 2 9B (Google)",
    "chatgpt-browser": "ChatGPT (Local Browser API bypass)",
}

DEFAULT_MODEL = "llama-3.3-70b-versatile"

# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert AI fraud auditor for Indian field survey calls. "
    "You have deep domain knowledge about how legitimate Indian field surveys work. "
    "Respond ONLY with valid JSON. No markdown, no explanation outside the JSON."
)

# ──────────────────────────────────────────────────────────────────────────────
# DOMAIN-AWARE USER PROMPT (v3)
# ──────────────────────────────────────────────────────────────────────────────

FRAUD_ANALYSIS_PROMPT = """Analyze this survey call for fraud.

=== DOMAIN KNOWLEDGE (read carefully before scoring) ===

TRILINGUAL QUESTION EFFECT:
Every question in this survey is asked in THREE languages (Marathi + English + Hindi).
The surveyor must read the full question in all three languages.
This means: surveyor speaking 60-75% of total audio time is COMPLETELY NORMAL and not suspicious.
Only flag surveyor speech dominance if the proportion exceeds 85% AND the transcript shows
no genuine respondent participation (not just short answers).

QUESTION TYPES — SKIP THESE IN SCORING:
Questions containing "UPLOAD" in their text are photo upload tasks, not spoken questions.
They will always show "No answer" and must be excluded from completeness calculation.
Example: "UPLOAD ADHAR CARD", "UPLOAD RESPONDENT'S IMAGE" → ignore these entirely.

ANSWER OPTION LABELS:
Answer options in this system include surveyor instructions in parentheses, like:
"FEATURE PHONE (TRAIN THE SURVEYOR TO PROVIDE TOLL FREE NUMBER)"
This is how the database labels answer options. It is NOT data contamination.
Do not flag parenthetical text inside answers as fraud evidence.

TURN COUNT INTERPRETATION:
High turn count (200+ turns) with short average turn duration (1-3 sec) = rapid back-and-forth.
This is a POSITIVE signal — indicates active exchange between two real people.
A fake form or mimicry call typically has very few long turns (surveyor monologuing).

LEGITIMATE SURVEYOR PHRASES:
"मी ते सांगतो" / "सांगा ना" / "हो ना" are normal conversational Marathi encouragers.
They are NOT evidence of the surveyor feeding answers unless combined with other fraud signals.

ASR QUALITY NOTE:
The transcript may contain garbled or mixed-language text due to multilingual audio.
Do not penalize for ASR quality issues. Focus on structural patterns, not ASR accuracy.

DURATION BENCHMARKS FOR THIS SURVEY (19 questions, trilingual):
< 400s  = Very suspicious (cannot read all questions in 3 languages this fast)
400-600s = Short but possible
600-900s = Normal
900-1200s = Thorough
> 1200s = Very thorough or stalled

=== FRAUD TYPES ===

fake_form:
  Definition: No real respondent present. Surveyor filled form alone, made a fake call,
  or conducted a call with no one on the other end.
  Key evidence (need 2+ of these):
  - Single speaker throughout (pyannote num_speakers = 1)
  - Call duration < 400s for a 19-question trilingual survey
  - No second-party voice in transcript at all
  - Background only (traffic, walking, ambient noise dominates)
  - Answers suspiciously complete despite no actual dialogue

mimicry:
  Definition: Surveyor asks AND answers himself. One person plays both roles.
  Key evidence (need 2+ of these):
  - Single speaker (pyannote num_speakers = 1)
  - No natural pause pattern between question and answer
  - Uniform turn lengths (no variation in response timing)
  - Voice pitch/style identical for both "sides" of conversation
  - Transcript shows both Q and A in same voice register

force_survey:
  Definition: A real respondent exists (2 speakers detected), BUT the surveyor or a proxy
  is supplying answers on behalf of the registered respondent without asking or listening.
  Key evidence (need 2+ of these):
  - Registered gender FEMALE but audio has predominantly MALE respondent voice
  - Surveyor states answers before asking (fills form then reads it back)
  - Respondent makes sounds of confusion or protest ("nai nai", "arre", "kya")
  - Complex multi-select answers given in 1-3 seconds (impossible to answer legitimately)
  - Answers are suspiciously "correct" for government schemes the respondent shows no awareness of

clean:
  Definition: Legitimate interview. Two distinct speakers, natural Q&A flow,
  respondent answers freely, reasonable duration, no major contradictions.

=== SURVEY DATA ===

UID: {uid}
Surveyor: {surveyor}
Date/Time: {date} {time}
Duration: {duration} seconds
Registered Gender: {registered_gender}
Registered DOB: {dob}
Location: {address}
GPS movement during call: {movement} meters

=== SPEAKER DIARIZATION (pyannote — machine-detected) ===
{speaker_analysis}

=== RECORDED ANSWERS ===
{answers}

=== AUDIO TRANSCRIPT ===
{transcript}

=== CROSS-CALL CONTEXT ===
{cross_call_context}

=== TASK ===

Step 1: Count how many SPOKEN questions exist (exclude all UPLOAD questions).
Step 2: Count how many of those have a real answer (not "No answer").
Step 3: Use speaker data to assess voice authenticity.
Step 4: Check if registered gender matches respondent voice pattern.
Step 5: Check if any answers were physically impossible given the duration.
Step 6: Determine fraud_type based on the fraud definitions above.

RESPOND WITH ONLY THIS JSON:
{{
  "fraud_detected": true or false,
  "fraud_type": "fake_form" or "mimicry" or "force_survey" or "clean",
  "executive_summary": "3-5 sentences. Cite specific numbers: speaker count, duration, gender match, suspicious answers. State your reasoning chain clearly.",

  "spoken_questions_total": <int, excluding UPLOAD type>,
  "spoken_questions_answered": <int>,

  "section_analysis": [
    {{
      "section": "Voice & Speaker Analysis",
      "score": <float 0-10>,
      "verdict": "pass" or "partial" or "fail",
      "findings": [
        "State exact speaker count and speaking percentages from pyannote data",
        "State turn count and average turn duration and what this implies",
        "Note: surveyor speaking 60-75% is NORMAL for trilingual surveys — only flag above 85%"
      ],
      "evidence": [
        {{"type": "diarization", "text": "cite EXACT numbers from speaker analysis", "severity": "critical or warning or info", "timestamp_start": <float>, "timestamp_end": <float>}}
      ]
    }},
    {{
      "section": "Script Compliance",
      "score": <float 0-10>,
      "verdict": "pass or partial or fail",
      "findings": [
        "How many spoken questions answered out of total spoken questions (exclude UPLOAD)",
        "Which specific spoken questions were skipped or had no answer"
      ],
      "evidence": [
        {{"type": "question", "text": "cite actual skipped question text", "severity": "warning or critical", "timestamp_start": <float>, "timestamp_end": <float>}}
      ]
    }},
    {{
      "section": "Data Integrity",
      "score": <float 0-10>,
      "verdict": "pass or partial or fail",
      "findings": [
        "Does registered gender match the respondent voice in the audio?",
        "Are there internal contradictions between answers (e.g. age vs DOB)?"
      ],
      "evidence": [
        {{"type": "mismatch", "text": "cite specific values that conflict", "severity": "critical or warning or info", "timestamp_start": <float>, "timestamp_end": <float>}}
      ]
    }},
    {{
      "section": "Questioning Technique",
      "score": <float 0-10>,
      "verdict": "pass or partial or fail",
      "findings": [
        "Did surveyor ask questions neutrally or did they suggest answers?",
        "Were answers given unrealistically fast for complex multi-select questions?"
      ],
      "evidence": [
        {{"type": "transcript", "text": "cite real example from transcript", "severity": "warning or critical or info", "timestamp_start": <float>, "timestamp_end": <float>}}
      ]
    }},
    {{
      "section": "Response Authenticity",
      "score": <float 0-10>,
      "verdict": "pass or partial or fail",
      "findings": [
        "Do answers sound naturally volunteered or scripted/coerced?",
        "Does respondent show awareness of topics they claim to know about?"
      ],
      "evidence": [
        {{"type": "transcript", "text": "cite real answer showing the issue or showing authenticity", "severity": "critical or warning or info", "timestamp_start": <float>, "timestamp_end": <float>}}
      ]
    }}
  ],

  "quality_score": <float 0-10, weighted avg: Voice 25% + Script 20% + Data 20% + Technique 15% + Authenticity 20%>,
  "completeness_score": <float 0-10, based on spoken questions only>,
  "fraud_risk_score": <float 0-10, where 10 = definite fraud, 0 = definitely clean>,
  "technique_score": <float 0-10>,
  "key_flags": ["only list REAL issues found, not generic placeholders"]
}}

RULES:
1. EXCLUDE all UPLOAD-type questions from completeness scoring.
2. Surveyor at 60-75% speech is NORMAL — do not flag it.
3. High turn count (100+) with short turns is a POSITIVE signal.
4. Answer option labels with parenthetical instructions are NORMAL — not contamination.
5. At least 2 real findings and 2 real evidence items per section — no placeholders.
6. Scores must be precise decimals (e.g. 6.7, 3.2). quality_score = weighted average of 5 sections.
7. fraud_risk_score should only be above 7 if you have at least 2 STRONG fraud signals.
8. Timestamp estimates: distribute evenly across duration based on question order.
"""


# ──────────────────────────────────────────────────────────────────────────────
# SCORE CALIBRATION (post-LLM, domain-specific corrections)
# ──────────────────────────────────────────────────────────────────────────────

def calibrate_scores(result: dict, speaker_data: dict, duration: int) -> dict:
    """
    Apply domain-specific calibration to prevent false positives.
    """
    num_speakers = speaker_data.get("num_speakers", 0) if speaker_data else 0
    turns = speaker_data.get("speaker_turns", 0) if speaker_data else 0

    # Rule 1: If 2 speakers detected, fake_form is almost impossible
    if num_speakers >= 2 and result["fraud_type"] == "fake_form":
        result["fraud_type"] = "force_survey"  # Downgrade — someone IS there
        result["fraud_risk_score"] = min(result["fraud_risk_score"], 7.0)
        result["executive_summary"] += " [Calibrated: 2 speakers detected — cannot be fake_form]"

    # Rule 2: If 2 speakers + high turn count, mimicry is very unlikely
    if num_speakers >= 2 and turns > 50 and result["fraud_type"] == "mimicry":
        result["fraud_type"] = "force_survey"
        result["fraud_risk_score"] = min(result["fraud_risk_score"], 6.5)
        result["executive_summary"] += " [Calibrated: 2 speakers + 50+ turns — mimicry unlikely]"

    # Rule 3: Cap fraud_risk_score for 2-speaker calls with good duration
    if num_speakers >= 2 and duration >= 600:
        result["fraud_risk_score"] = min(result["fraud_risk_score"], 8.5)

    # Rule 4: If fraud_risk_score < 5 but fraud_detected = True, fix it
    if result["fraud_risk_score"] < 5.0:
        result["fraud_detected"] = False
        result["fraud_type"] = "clean"

    return result


# ──────────────────────────────────────────────────────────────────────────────
# MAIN ANALYSIS FUNCTION
# ──────────────────────────────────────────────────────────────────────────────

def analyze_fraud(
    uid: int,
    surveyor: str,
    date: str,
    time: str,
    duration: int,
    registered_gender: str,
    dob: str,
    address: str,
    movement: str,
    answers: list,
    transcript: str,
    model: str = DEFAULT_MODEL,
    speaker_data: dict = None,
    db=None,
    surveyor_id: str = None,
) -> dict:
    """
    Use Groq LLM to analyze fraud in a survey call.
    Returns fraud analysis dict with detailed per-section breakdown.
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)

        # ── Pre-process answers (filter UPLOAD tasks) ──
        from preprocessing import format_answers_for_prompt
        answers_text = format_answers_for_prompt(answers)

        # ── Format speaker analysis data ──
        from speaker_analysis import format_speaker_data_for_prompt
        speaker_analysis_text = (
            format_speaker_data_for_prompt(speaker_data)
            if speaker_data
            else "SPEAKER ANALYSIS: Not available (no audio file or analysis not run)"
        )

        # ── Get cross-call context (if DB available) ──
        cross_call_text = "No cross-call context available."
        if db and surveyor_id:
            try:
                from agent_profiler import get_cross_call_context
                cross_call_text = get_cross_call_context(uid, surveyor_id, db)
            except Exception as e:
                print(f"[Fraud Detection] Cross-call context failed: {e}")

        # ── Build the prompt ──
        prompt = FRAUD_ANALYSIS_PROMPT.format(
            uid=uid,
            surveyor=surveyor,
            date=date,
            time=time,
            duration=duration,
            registered_gender=registered_gender,
            dob=dob,
            address=address,
            movement=movement,
            speaker_analysis=speaker_analysis_text,
            answers=answers_text,
            transcript=transcript[:5000] if transcript else "No transcript available",
            cross_call_context=cross_call_text,
        )

        # ── Route to ChatGPT Browser or Groq API ──
        if model == "chatgpt-browser":
            full_prompt = f"{SYSTEM_PROMPT}\nRespond EXACTLY in the JSON format requested. Do NOT output anything else except JSON.\n\n{prompt}"

            from chatgpt_browser import run_chatgpt_analysis
            import asyncio
            import sys

            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            print(f"[Fraud Detection] Using ChatGPT via Browser Automation for UID={uid}")
            try:
                result_text = asyncio.run(run_chatgpt_analysis(full_prompt))
            except Exception as e:
                print(f"[ChatGPT Browser Error] {e}")
                raise e
        else:
            # Use Groq API
            if model not in AVAILABLE_MODELS:
                model = DEFAULT_MODEL

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4000,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            result_text = response.choices[0].message.content.strip()

        print(f"[Fraud Detection] Model={model}, UID={uid}, Raw response length={len(result_text)}")

        # ── Parse JSON ──
        json_str = result_text
        if "```" in json_str:
            fence_match = re_mod.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re_mod.DOTALL)
            if fence_match:
                json_str = fence_match.group(1)
            else:
                start = json_str.find("{")
                end = json_str.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]

        if not json_str.startswith("{"):
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = json_str[start:end]

        result = json.loads(json_str)

        # ── Validate required fields ──
        result["fraud_detected"] = bool(result.get("fraud_detected", False))
        result["fraud_type"] = str(result.get("fraud_type", "clean"))
        result["executive_summary"] = str(result.get("executive_summary", result.get("fraud_reason", "No summary provided")))
        result["fraud_reason"] = result["executive_summary"]
        result["quality_score"] = float(result.get("quality_score", 5.0))
        result["completeness_score"] = float(result.get("completeness_score", 5.0))
        result["fraud_risk_score"] = float(result.get("fraud_risk_score", 5.0))
        result["technique_score"] = float(result.get("technique_score", 5.0))

        # ── Validate section_analysis ──
        section_analysis = result.get("section_analysis", [])
        if not isinstance(section_analysis, list) or len(section_analysis) == 0:
            section_analysis = _build_fallback_sections(result)
        else:
            for section in section_analysis:
                section["section"] = str(section.get("section", "Unknown"))
                section["score"] = float(section.get("score", 5.0))
                section["verdict"] = str(section.get("verdict", "partial"))
                section["findings"] = section.get("findings", ["No findings available"])
                if not isinstance(section["findings"], list):
                    section["findings"] = [str(section["findings"])]
                section["evidence"] = section.get("evidence", [])
                if not isinstance(section["evidence"], list):
                    section["evidence"] = []
                # Validate each evidence item — KEEP timestamps
                validated_evidence = []
                for ev in section["evidence"]:
                    if isinstance(ev, dict):
                        ev_clean = {
                            "type": str(ev.get("type", "observation")),
                            "text": str(ev.get("text", "No details")),
                            "severity": str(ev.get("severity", "info")),
                        }
                        if "timestamp_start" in ev and ev["timestamp_start"] is not None:
                            try:
                                ev_clean["timestamp_start"] = float(ev["timestamp_start"])
                            except (ValueError, TypeError):
                                pass
                        if "timestamp_end" in ev and ev["timestamp_end"] is not None:
                            try:
                                ev_clean["timestamp_end"] = float(ev["timestamp_end"])
                            except (ValueError, TypeError):
                                pass
                        validated_evidence.append(ev_clean)
                section["evidence"] = validated_evidence

        result["section_analysis"] = section_analysis

        # ── Clamp scores ──
        for key in ["quality_score", "completeness_score", "fraud_risk_score", "technique_score"]:
            result[key] = max(0.0, min(10.0, result[key]))
        for section in result["section_analysis"]:
            section["score"] = max(0.0, min(10.0, section["score"]))

        # ── Key flags ──
        result["key_flags"] = result.get("key_flags", [])
        if not isinstance(result["key_flags"], list):
            result["key_flags"] = []

        # ── Apply domain-specific score calibration ──
        result = calibrate_scores(result, speaker_data, int(duration) if duration else 0)

        print(f"[Fraud Detection] UID={uid}: type={result['fraud_type']}, quality={result['quality_score']}, risk={result['fraud_risk_score']}, sections={len(result['section_analysis'])}")
        return result

    except json.JSONDecodeError as e:
        print(f"[Fraud Detection] JSON parse error: {e}")
        print(f"[Fraud Detection] Raw response: {result_text[:500]}")
        return _default_result("Analysis completed but response parsing failed")
    except Exception as e:
        print(f"[Fraud Detection Error] {e}")
        return _default_result(f"Analysis failed: {str(e)}")


# ──────────────────────────────────────────────────────────────────────────────
# FALLBACK HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _build_fallback_sections(result: dict) -> list:
    """Build fallback section_analysis from flat scores when LLM doesn't return sections."""
    fraud_reason = result.get("fraud_reason", "No details available")
    return [
        {
            "section": "Voice & Speaker Analysis",
            "score": result.get("quality_score", 5.0),
            "verdict": "fail" if result.get("fraud_detected") else "pass",
            "findings": [fraud_reason],
            "evidence": [{"type": "observation", "text": "Detailed section analysis was not available. Re-analyze for full breakdown.", "severity": "info"}],
        },
        {
            "section": "Script Compliance",
            "score": result.get("completeness_score", 5.0),
            "verdict": "partial",
            "findings": ["Completeness score based on answered questions"],
            "evidence": [{"type": "observation", "text": f"Completeness score: {result.get('completeness_score', 5.0)}/10", "severity": "info"}],
        },
        {
            "section": "Data Integrity",
            "score": max(0.0, 10.0 - result.get("fraud_risk_score", 5.0)),
            "verdict": "fail" if result.get("fraud_risk_score", 5.0) > 7 else "partial",
            "findings": ["Data integrity derived from fraud risk assessment"],
            "evidence": [{"type": "observation", "text": f"Fraud risk score: {result.get('fraud_risk_score', 5.0)}/10", "severity": "warning"}],
        },
        {
            "section": "Questioning Technique",
            "score": result.get("technique_score", 5.0),
            "verdict": "partial",
            "findings": ["Technique score based on questioning quality assessment"],
            "evidence": [{"type": "observation", "text": f"Technique score: {result.get('technique_score', 5.0)}/10", "severity": "info"}],
        },
        {
            "section": "Response Authenticity",
            "score": result.get("quality_score", 5.0),
            "verdict": "fail" if result.get("fraud_detected") else "pass",
            "findings": [fraud_reason],
            "evidence": [{"type": "observation", "text": "Re-analyze this record for detailed response authenticity breakdown.", "severity": "info"}],
        },
    ]


def _default_result(reason: str) -> dict:
    """Return a default result when analysis fails."""
    return {
        "fraud_detected": False,
        "fraud_type": "clean",
        "fraud_reason": reason,
        "executive_summary": reason,
        "quality_score": 5.0,
        "completeness_score": 5.0,
        "fraud_risk_score": 5.0,
        "technique_score": 5.0,
        "key_flags": ["analysis_failed"],
        "section_analysis": _build_fallback_sections({
            "fraud_detected": False,
            "fraud_reason": reason,
            "quality_score": 5.0,
            "completeness_score": 5.0,
            "fraud_risk_score": 5.0,
            "technique_score": 5.0,
        }),
    }
