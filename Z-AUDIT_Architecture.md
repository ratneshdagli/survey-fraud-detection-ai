# Z-AUDIT — End-to-End Architecture & Code Flow

> **Last Updated:** March 2026  
> **Purpose:** Full technical walkthrough of every layer — from user clicking a button in the browser to Groq LLM returning a detailed analysis and it rendering on screen.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Z-AUDIT PLATFORM                                │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────┐               │
│  │  FRONTEND  (React + Vite + TailwindCSS)                 │               │
│  │  http://localhost:5173                                   │               │
│  │                                                          │               │
│  │  App.jsx → Dashboard.jsx → RecordDetail.jsx             │               │
│  │              ↕                    ↕                      │               │
│  │           api.js (fetch calls to /api/*)                │               │
│  └────────────────────────┬─────────────────────────────────┘               │
│                           │  HTTP REST (JSON)                               │
│                           ▼                                                 │
│  ┌──────────────────────────────────────────────────────────┐               │
│  │  BACKEND   (FastAPI + Python)                           │               │
│  │  http://localhost:8000                                   │               │
│  │                                                          │               │
│  │  main.py  ──►  transcription.py  ──►  Groq Whisper     │               │
│  │     │                                                    │               │
│  │     ├──────►  speaker_analysis.py ──►  pyannote (GPU)  │               │
│  │     │                                                    │               │
│  │     └──────►  fraud_detection.py ──►  Groq LLaMA 70B   │               │
│  │     │              (incl. speaker data in prompt)        │               │
│  │     └──────►  models.py          ──►  zaudi.db (SQLite) │               │
│  └──────────────────────────────────────────────────────────┘               │
│                                                                             │
│  DATA SOURCES:                                                              │
│    C:\Path\To\Project\MH Project 17-03-26\{uid}.wav    ← Audio files               │
│    C:\Path\To\Project\data_with_json.csv               ← Metadata + Q&A            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend UI | React 18 + Vite + TailwindCSS |
| Charts | Recharts (BarChart) |
| Backend API | FastAPI (Python 3.10+) |
| Database | SQLite via SQLAlchemy |
| Transcription | Groq Whisper Large v3 |
| Speaker Diarization | pyannote/speaker-diarization-3.1 (local GPU) |
| LLM Analysis | Groq (LLaMA 3.3 70B / LLaMA 3.1 8B / Mixtral) |
| ORM | SQLAlchemy |

---

## Directory Structure

```
C:\Path\To\Project\
├── zaudi-mvp\
│   ├── frontend\
│   │   └── src\
│   │       ├── main.jsx              ← React entry point
│   │       ├── App.jsx               ← Root component, state manager
│   │       ├── api.js                ← Centralized HTTP helper
│   │       ├── index.css             ← Global styles (TailwindCSS)
│   │       └── components\
│   │           ├── Dashboard.jsx     ← Stats cards, table, filters
│   │           ├── RecordDetail.jsx  ← Slide-out detail panel + analysis UI
│   │           └── UploadModal.jsx   ← Audio upload form
│   └── backend\
│       ├── main.py                   ← FastAPI app, all HTTP routes
│       ├── models.py                 ← SQLAlchemy ORM models
│       ├── fraud_detection.py        ← Groq LLM analysis + prompt
│       ├── speaker_analysis.py       ← pyannote speaker diarization (GPU)
│       ├── transcription.py          ← Groq Whisper transcription
│       ├── seed_real.py              ← CSV → DB seeder (live AI)
│       ├── .env                      ← GROQ_API_KEY + HF_TOKEN
│       └── zaudi.db                  ← SQLite database file
├── MH Project 17-03-26\
│   ├── 111379.wav
│   ├── 112136.wav
│   └── ...                           ← Survey audio files
└── data_with_json.csv                ← Raw metadata + Q&A answers
```

---

# FLOW 1: Initial Page Load

## 1.1 Frontend Mount (App.jsx)

When the app mounts, `App.jsx` fires two parallel API calls:

```jsx
// App.jsx — lines 34-80
export default function App() {
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');

  // Load available LLM models on mount
  useEffect(() => {
    api.getModels()
      .then(data => {
        setModels(data.models);
        setSelectedModel(data.default);  // default = "llama-3.3-70b-versatile"
      })
      .catch(() => {});
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    const data = await api.getStats();
    setStats(data);
  }, []);

  // Fetch records
  const fetchRecords = useCallback(async () => {
    setLoading(true);
    const data = await api.getRecords({
      page,
      limit: 20,
      fraud_type: fraudFilter,
      min_score: minScore > 0 ? minScore : undefined,
      search: searchQuery || undefined,
    });
    setRecords(data.records);
    setTotalRecords(data.total);
    setTotalPages(data.total_pages);
    setLoading(false);
  }, [page, fraudFilter, minScore, searchQuery]);

  // Load on mount and filter change
  useEffect(() => {
    fetchStats();
    fetchRecords();
  }, [fetchStats, fetchRecords]);
}
```

### 1.1.1 Agent Leaderboard
A tabular view (`AgentLeaderboard.jsx`) that ranks surveyors by a composite risk score (derived from fraud rate and average quality score), helping supervisors quickly identify problematic agents. 

### 1.1.2 Cross-Call Heatmap
An Area chart (`CrossCallHeatmap.jsx`) using Recharts to visualize the trend of total calls vs. flagged fraud calls over time, providing a clear calendar view of survey quality.


## 1.2 API Calls (api.js)

```javascript
// api.js — all API calls go through this file
const API_BASE = '/api';

async function handleResponse(res) {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  getStats: () =>
    fetch(`${API_BASE}/stats`).then(handleResponse),

  getRecords: ({ page = 1, limit = 20, fraud_type, min_score, max_score, search } = {}) => {
    const params = new URLSearchParams({ page, limit });
    if (fraud_type && fraud_type !== 'all') params.append('fraud_type', fraud_type);
    if (min_score != null) params.append('min_score', min_score);
    if (max_score != null) params.append('max_score', max_score);
    if (search) params.append('search', search);
    return fetch(`${API_BASE}/records?${params}`).then(handleResponse);
  },

  getModels: () =>
    fetch(`${API_BASE}/models`).then(handleResponse),

  reanalyzeRecord: (uid, model) =>
    fetch(`${API_BASE}/records/${uid}/reanalyze?model=${encodeURIComponent(model)}`, {
      method: 'POST',
    }).then(handleResponse),
};
```

## 1.3 Backend Stats Endpoint (main.py)

```python
# main.py — GET /api/stats
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(AuditRecord.id)).scalar() or 0
    fraud_count = db.query(func.count(AuditRecord.id)).filter(
        AuditRecord.fraud_detected == True
    ).scalar() or 0
    clean_count = total - fraud_count
    avg_quality = db.query(func.avg(AuditRecord.quality_score)).scalar() or 0.0

    fraud_breakdown = {}
    for fraud_type_val in ["fake_form", "mimicry", "force_survey", "clean"]:
        count = db.query(func.count(AuditRecord.id)).filter(
            AuditRecord.fraud_type == fraud_type_val
        ).scalar() or 0
        fraud_breakdown[fraud_type_val] = count

    return {
        "total_calls": total,
        "fraud_detected": fraud_count,
        "clean_calls": clean_count,
        "fraud_percentage": round((fraud_count / total * 100) if total > 0 else 0, 1),
        "clean_percentage": round((clean_count / total * 100) if total > 0 else 0, 1),
        "avg_quality_score": round(avg_quality, 2),
        "fraud_breakdown": fraud_breakdown,
    }
```

## 1.4 Backend Records Endpoint (main.py)

```python
# main.py — GET /api/records
@app.get("/api/records")
def list_records(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    fraud_type: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(AuditRecord)

    # Apply filters
    if fraud_type and fraud_type != "all":
        query = query.filter(AuditRecord.fraud_type == fraud_type)
    if min_score is not None:
        query = query.filter(AuditRecord.quality_score >= min_score)
    if max_score is not None:
        query = query.filter(AuditRecord.quality_score <= max_score)
    if search:
        search_term = f"%{search}%"
        if search.isdigit():
            query = query.filter(AuditRecord.uid == int(search))
        else:
            query = query.filter(AuditRecord.surveyor_name.like(search_term))

    total = query.count()
    records = query.order_by(AuditRecord.created_at.desc()) \
                   .offset((page - 1) * limit).limit(limit).all()

    return {
        "records": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
    }
```

## 1.5 Database Schema (models.py)

```python
# models.py — AuditRecord table definition
class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(Integer, unique=True, index=True)
    surveyor_name = Column(String)
    surveyor_id = Column(String)
    survey_date = Column(String)
    survey_time = Column(String)
    time_difference_seconds = Column(Integer)
    actual_address = Column(Text)
    respondent_gender = Column(String)
    respondent_dob = Column(String)
    respondent_area = Column(String)
    respondent_occupation = Column(String)
    audio_url = Column(String)
    transcript = Column(Text)

    # Fraud analysis results
    fraud_detected = Column(Boolean, default=False)
    fraud_type = Column(String)       # fake_form | mimicry | force_survey | clean
    fraud_reason = Column(Text)       # executive_summary from LLM

    # Flat scores (0.0 – 10.0)
    quality_score = Column(Float)
    completeness_score = Column(Float)
    fraud_risk_score = Column(Float)
    technique_score = Column(Float)

    # NEW: Full JSON breakdown from LLM (per-section analysis)
    detailed_analysis = Column(Text)  # stored as JSON string, parsed in to_dict()

    created_at = Column(DateTime, default=datetime.utcnow)
    raw_json = Column(Text)           # full original metadata blob

    def to_dict(self):
        return {
            "uid": self.uid,
            "surveyor_name": self.surveyor_name,
            "surveyor_id": self.surveyor_id,
            "survey_date": self.survey_date,
            "survey_time": self.survey_time,
            "time_difference_seconds": self.time_difference_seconds,
            "actual_address": self.actual_address,
            "respondent_gender": self.respondent_gender,
            "respondent_dob": self.respondent_dob,
            "respondent_area": self.respondent_area,
            "respondent_occupation": self.respondent_occupation,
            "audio_url": self.audio_url,
            "transcript": self.transcript,
            "fraud_detected": self.fraud_detected,
            "fraud_type": self.fraud_type,
            "fraud_reason": self.fraud_reason,
            "quality_score": self.quality_score,
            "completeness_score": self.completeness_score,
            "fraud_risk_score": self.fraud_risk_score,
            "technique_score": self.technique_score,
            # Parsed from JSON string to dict object before sending to frontend
            "detailed_analysis": json.loads(self.detailed_analysis)
                                  if self.detailed_analysis else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "raw_json": self.raw_json,
        }
```

---

# FLOW 2: Data Seeding (CSV → DB)

This is the offline process that populates the database before the UI is used.

```
data_with_json.csv
      │
      ▼
seed_real.py:parse_csv_row()
      │  UID (int) + JSON blob
      ▼
seed_real.py:extract_metadata()
      │  surveyor, date, time, duration, gender, dob,
      │  address, area, occupation, audioanswers[]
      ▼
transcription.py:transcribe_audio(uid.wav)   ← Groq Whisper
      │  OR
transcription.py:mock_transcript_from_answers(audioanswers)
      │
      ▼  transcript (plain text)
fraud_detection.py:analyze_fraud(...)
      │  → Groq LLaMA (EXACT PROMPT — see FLOW 3)
      ▼
AuditRecord(**result) → db.add() → db.commit()
      └── saved to zaudi.db
```

**seed_real.py core loop:**
```python
# seed_real.py — process_record() — the key function
def process_record(meta):
    uid = meta["uid"]
    audio_file_path = os.path.join(AUDIO_DIR, f"{uid}.wav")

    # STEP 1: TRANSCRIPTION
    if USE_REAL_TRANSCRIPTION and os.path.exists(audio_file_path):
        transcript = transcribe_audio(audio_file_path)   # Groq Whisper
    else:
        transcript = mock_transcript_from_answers(meta["audio_answers"])

    # STEP 2: FRAUD ANALYSIS
    movement = str(meta["raw_data"].get("movement", "0"))
    result = analyze_fraud(
        uid=uid,
        surveyor=meta["surveyor_name"],
        date=meta["survey_date"],
        time=meta["survey_time"],
        duration=meta["time_difference_seconds"],
        registered_gender=meta["respondent_gender"],
        dob=meta["respondent_dob"],
        address=meta["actual_address"],
        movement=movement,
        answers=meta["audio_answers"],
        transcript=transcript,
        model=LLM_MODEL,   # "llama-3.1-8b-instant" for speed during seeding
    )
    return {... record_data ...}
```

---

# FLOW 3: AI Pipeline — Transcription + Fraud Analysis

This is the heart of Z-AUDIT. This same pipeline runs during seeding, upload, AND re-analysis.

## 3.1 Audio Transcription (transcription.py)

```python
# transcription.py — Groq Whisper Large v3
def transcribe_audio(audio_file_path: str) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_file_path), audio_file.read()),
            model="whisper-large-v3",
            response_format="text",
        )
    return transcription  # Returns plain text transcript
```

**If no audio file**, a mock transcript is built from the Q&A answers:
```python
# transcription.py — mock_transcript_from_answers()
def mock_transcript_from_answers(audio_answers: list) -> str:
    # audio_answers format: [[answer, question], [answer, question], ...]
    lines = ["=== MOCK TRANSCRIPT (Generated from recorded answers) ===\n"]
    q_num = 0
    for pair in audio_answers:
        answer = pair[0]
        question = pair[1]
        if "UPLOAD" in str(question).upper():
            continue   # Skip photo upload questions
        q_num += 1
        lines.append(f"Surveyor (Q{q_num}): {str(question)[:200]}")
        lines.append(f"Respondent: {str(answer)[:200]}")
        lines.append("")
    lines.append(f"=== END OF MOCK TRANSCRIPT ({q_num} questions) ===")
    return "\n".join(lines)
```

## 3.2 Fraud Analysis — The Full LLM Prompt (fraud_detection.py)

This is the **EXACT PROMPT** (word for word) sent to Groq LLaMA:

```
You are an expert AI quality auditor for field survey calls conducted in rural India.
Your job is to provide a DETAILED, EXPLAINABLE audit — not just scores, but specific evidence for every finding.

FRAUD TYPES (pick exactly one):
1. fake_form: No real respondent present. Surveyor filled form alone or made a fake call. Evidence: no second voice, background noise only, no real Q&A.
2. mimicry: Surveyor is BOTH asking AND answering himself. Only one voice plays both roles. Evidence: single voice pattern, no natural pauses, surveyor answers immediately.
3. force_survey: Real respondent exists but surveyor answers ON BEHALF of them, or a proxy answers instead. Evidence: gender mismatch, surveyor fills answers without asking, coerced responses.
4. clean: Legitimate survey. Two distinct voices, natural Q&A flow, respondent answers freely.

SURVEY DATA:
- UID: {uid}
- Surveyor: {surveyor}
- Date/Time: {date} {time}
- Duration: {duration} seconds
- Registered Gender: {registered_gender}
- DOB: {dob}
- Location: {address}
- GPS Movement: {movement} meters

{speaker_analysis}

RECORDED ANSWERS:
{answers}

TRANSCRIPT:
{transcript}

RESPOND WITH ONLY THIS JSON (no other text, no markdown):
{
  "fraud_detected": true or false,
  "fraud_type": "one of: fake_form, mimicry, force_survey, clean",
  "executive_summary": "<REPLACE: 3-5 sentence detailed verdict citing SPECIFIC evidence from this record>",

  "section_analysis": [
    {
      "section": "Voice & Speaker Analysis",
      "score": <float 0-10>,
      "verdict": "pass" or "partial" or "fail",
      "findings": [
        "<REPLACE: cite exact number of speakers detected and their speaking percentages>",
        "<REPLACE: describe turn-taking pattern — balanced vs skewed, natural vs rehearsed>"
      ],
      "evidence": [
        {"type": "diarization", "text": "<REPLACE: write EXACTLY what pyannote detected>", "severity": "critical or info", "timestamp_start": <float>, "timestamp_end": <float>},
        {"type": "metadata", "text": "<REPLACE: specific metadata finding>", "severity": "warning", "timestamp_start": 0.0, "timestamp_end": 10.0}
      ]
    },
    // ... Script Compliance, Data Integrity, Questioning Technique, Response Authenticity
    // (each with <REPLACE:> markers and mandatory timestamp_start/timestamp_end)
  ],

  "quality_score": <float 0-10>,
  "completeness_score": <float 0-10>,
  "fraud_risk_score": <float 0-10>,
  "technique_score": <float 0-10>,
  "key_flags": ["list", "of", "specific", "red_flags"]
}

CRITICAL INSTRUCTIONS:
1. EVERY section MUST have at least 2 findings and at least 2 evidence items. Do NOT leave any empty.
2. Evidence "text" must cite SPECIFIC data from this record — question text, answer text, duration, GPS movement, gender, etc. Do NOT be generic.
3. Severity levels: "critical" = definite problem, "warning" = suspicious, "info" = worth noting but not necessarily bad.
4. Each score must be a precise decimal (e.g. 3.4, 6.7, 8.1). Scores MUST vary by section based on the actual evidence.
5. The executive_summary must explain the verdict in plain language a QA manager can understand.
6. Duration analysis: <300s very suspicious, 300-600s short, 600-1200s normal, >1200s thorough.
7. The quality_score should be the WEIGHTED AVERAGE of the 5 section scores (Voice=25%, Script=20%, Data=20%, Technique=15%, Authenticity=20%).
8. For "evidence", the "type" field can be: "transcript", "metadata", "question", "mismatch", "contradiction", "pattern", "diarization", or "observation".
9. SPEAKER ANALYSIS is from pyannote AI diarization — this is REAL machine-detected speaker data, NOT a guess.
10. TIMESTAMPS ARE MANDATORY: EVERY evidence item MUST include "timestamp_start" and "timestamp_end" (in seconds as floats). Estimate from speaker turn order and question sequence.
11. DO NOT COPY TEMPLATE TEXT. Every "<REPLACE: ...>" marker must be replaced with REAL, SPECIFIC text from THIS record's data.

### Domain-Aware Prompt Rules (v3)
The prompt contains explicit, trilingual domain logic:
* **Trilingual Expected Duration**: Surveyor speaking 60-75% is marked normal because each question is read in three languages.
* **Turn Counts**: Very high turn counts with fast overlaps are considered *positive* real-human interaction signals.
* **Upload Exclusion**: "UPLOAD" or "PHOTO" requests are entirely excluded from scoring to prevent false "unanswered" penalties.
* **Answer Labels**: Surveyor instruction text inside parentheses in answer options is ignored.
* **Agent Cross-Call History**: Profiling metrics run via `agent_profiler.py` inject historical fraud risk scores for the surveyor.
```

## 3.3 Data Preprocessing & Calibration Layer

Before sending data to the LLM, the system uses custom preprocessing utility modules:

1. **`preprocessing.py`**: Separates actual spoken questions from physical tasks ("Upload Photo"). Calculates whether average question durations are physically possible to read out loud.
2. **`agent_profiler.py`**: Queries the SQLite database across *all* of a given `surveyor_id`'s calls to generate a `composite_risk_score` and checks if they are duplicating answers across multiple recent calls.
3. **Post-LLM Calibration (`fraud_detection.py: calibrate_scores`)**: Corrects any "hallucinations" (e.g., if Pyannote absolutely guarantees 2 speakers exist, but the LLM confidently declares `fake_form` because of the trilingual speech duration issue, the python layer forces a downgrade to `force_survey` or `clean`).

## 3.4 LLM API Call (fraud_detection.py)

**Exact Groq API call:**
```python
# fraud_detection.py — analyze_fraud()
def analyze_fraud(uid, surveyor, date, time, duration, registered_gender,
                  dob, address, movement, answers, transcript,
                  model=DEFAULT_MODEL, speaker_data=None):

    client = Groq(api_key=GROQ_API_KEY)

    # Format answers (first 20 Q&A pairs)
    answers_text = ""
    for i, a in enumerate(answers[:20]):
        if isinstance(a, list) and len(a) >= 2:
            q = str(a[1])[:200]
            ans = str(a[0])[:200]
            answers_text += f"Q{i+1}: {q}\nA{i+1}: {ans}\n\n"

    # Format real speaker analysis data for the prompt
    from speaker_analysis import format_speaker_data_for_prompt
    speaker_analysis_text = format_speaker_data_for_prompt(speaker_data) \
        if speaker_data else "SPEAKER ANALYSIS: Not available"

    # Fill the prompt with actual survey data + speaker data
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
        answers=answers_text or "No answers recorded",
        transcript=transcript[:5000] or "No transcript available",
    )

    # Send to Groq
    response = client.chat.completions.create(
        model=model,                            # e.g. "llama-3.3-70b-versatile"
        messages=[
            {
                "role": "system",
                "content": "You are a fraud detection AI that provides DETAILED, EXPLAINABLE analysis. "
                           "Always respond with ONLY valid JSON. No explanations, no markdown fences, just raw JSON."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=4000,       # 4000 to accommodate full section analysis
        temperature=0.3,       # Low temperature = consistent, factual responses
        response_format={"type": "json_object"},  # Force JSON output mode
    )

    result_text = response.choices[0].message.content.strip()
    result = json.loads(result_text)
    # ... validation and clamping ...
    return result
```

## 3.4 ChatGPT Local Browser Bypass (chatgpt_browser.py)

To bypass Groq rate limits, users can select the **"ChatGPT (Local Browser API bypass)"** model. Instead of an API call, this triggers a Playwright automation script `chatgpt_browser.py` that connects to a local Chrome instance.

**Flow:**
1. `fraud_detection.py` intercepts `model == "chatgpt-browser"`.
2. It calls `asyncio.run(run_chatgpt_analysis(prompt))`, forcing a `WindowsProactorEventLoopPolicy` to support Playwright subprocesses in the background thread.
3. `chatgpt_browser.py` checks for Chrome on port `9222`. If not found, it **auto-launches an isolated Chrome profile** (`backend/chrome_profile`) to guarantee the debugging port works without interfering with the user's main browser.
4. Playwright navigates to `chatgpt.com`, pastes the prompt using the clipboard (`navigator.clipboard.writeText`), and sends it.
5. It polls the DOM until streaming finishes, extracts the text, and returns it to `fraud_detection.py` where it is parsed as JSON identically to a Groq response.

## 3.5 LLM Response Shape (what Groq/ChatGPT returns — example)

```json
{
  "fraud_detected": true,
  "fraud_type": "mimicry",
  "executive_summary": "The survey recording shows clear indicators of mimicry fraud. Only a single male voice is detected throughout all 19 questions, with no natural response pauses. The registered respondent is listed as Female, but all audio evidence points to the surveyor answering in his own voice.",

  "section_analysis": [
    {
      "section": "Voice & Speaker Analysis",
      "score": 1.8,
      "verdict": "fail",
      "findings": [
        "Only one voice detected throughout the entire 786-second recording",
        "Surveyor answers each question immediately with no natural hesitation typical of a real respondent",
        "No background household sounds consistent with a real home interview"
      ],
      "evidence": [
        {
          "type": "transcript",
          "text": "Q3: What is your age? A: 35 years — response in identical male voice, no pause",
          "severity": "critical"
        },
        {
          "type": "metadata",
          "text": "GPS movement: 0 meters across 786 seconds — surveyor did not move, suggesting no travel to respondent's home",
          "severity": "warning"
        }
      ]
    },
    {
      "section": "Script Compliance",
      "score": 7.2,
      "verdict": "partial",
      "findings": [
        "17 of 19 questions were asked in the correct sequence",
        "Questions 15 and 16 (household income section) were skipped entirely"
      ],
      "evidence": [
        {
          "type": "question",
          "text": "Q15: Monthly household income — no answer recorded in transcript",
          "severity": "warning"
        }
      ]
    },
    {
      "section": "Data Integrity",
      "score": 2.1,
      "verdict": "fail",
      "findings": [
        "Registered gender is FEMALE but voice analysis indicates only male voice present",
        "DOB indicates respondent should be 52 years old but self-reported age is 35"
      ],
      "evidence": [
        {
          "type": "mismatch",
          "text": "Registered gender: Female. Audio: Single male voice only. No female voice detected.",
          "severity": "critical"
        },
        {
          "type": "contradiction",
          "text": "Registered DOB: 1971 (age 52) but transcript answer to age question: '35 years'",
          "severity": "critical"
        }
      ]
    },
    {
      "section": "Questioning Technique",
      "score": 4.3,
      "verdict": "partial",
      "findings": [
        "Questions asked too rapidly with average 2-second intervals",
        "No probing or follow-up questions observed"
      ],
      "evidence": [
        {
          "type": "pattern",
          "text": "Q&A pairs show uniform 2-3 second answer patterns across all 17 questions — unnatural for real interview",
          "severity": "warning"
        }
      ]
    },
    {
      "section": "Response Authenticity",
      "score": 1.5,
      "verdict": "fail",
      "findings": [
        "All answers are very short (1-3 words) with no elaboration — atypical for legitimate interviews",
        "Responses do not contain any natural conversational elements like 'umm', 'acha', 'haan'"
      ],
      "evidence": [
        {
          "type": "transcript",
          "text": "Q8: Do you have any health issues? A: 'No.' (single word, no explanation)",
          "severity": "critical"
        }
      ]
    }
  ],

  "quality_score": 2.6,
  "completeness_score": 7.2,
  "fraud_risk_score": 9.1,
  "technique_score": 4.3,
  "key_flags": ["single_voice", "gender_mismatch", "age_contradiction", "no_natural_pauses", "zero_gps_movement"]
}
```

## 3.5 Result Processing and Storage (fraud_detection.py + main.py)

After getting the LLM result, it's validated and stored:

```python
# fraud_detection.py — validation logic
result["fraud_detected"] = bool(result.get("fraud_detected", False))
result["fraud_type"] = str(result.get("fraud_type", "clean"))
result["executive_summary"] = str(result.get("executive_summary", ""))
result["fraud_reason"] = result["executive_summary"]  # backward compat

# Score clamping — ensure 0-10
for key in ["quality_score", "completeness_score", "fraud_risk_score", "technique_score"]:
    result[key] = max(0.0, min(10.0, result[key]))

# Section validation
for section in result["section_analysis"]:
    section["score"] = max(0.0, min(10.0, float(section.get("score", 5.0))))
    section["verdict"] = str(section.get("verdict", "partial"))  # pass|partial|fail
    section["findings"] = section.get("findings", [])
    section["evidence"] = [
        {
            "type": str(ev.get("type", "observation")),
            "text": str(ev.get("text", "")),
            "severity": str(ev.get("severity", "info")),  # critical|warning|info
        }
        for ev in section.get("evidence", [])
        if isinstance(ev, dict)
    ]
```

```python
# main.py — building and storing detailed_analysis
detailed = {
    "executive_summary": result.get("executive_summary", ""),
    "section_analysis": result.get("section_analysis", []),
    "key_flags": result.get("key_flags", []),
}

record = AuditRecord(
    uid=uid,
    fraud_detected=result.get("fraud_detected", False),
    fraud_type=result.get("fraud_type", "clean"),
    fraud_reason=result.get("executive_summary", ""),   # plain text for table view
    quality_score=result.get("quality_score", 5.0),
    completeness_score=result.get("completeness_score", 5.0),
    fraud_risk_score=result.get("fraud_risk_score", 5.0),
    technique_score=result.get("technique_score", 5.0),
    detailed_analysis=json.dumps(detailed, ensure_ascii=False),  # stored as JSON string
    raw_json=json.dumps(meta, ensure_ascii=False),
    ...
)
db.add(record)
db.commit()
```

---

# FLOW 4: User Views a Record (Dashboard → Detail Panel)

## 4.1 User Clicks a Row (Dashboard.jsx)

```jsx
// Dashboard.jsx — table row click
records.map((record) => (
  <tr
    key={record.uid}
    className="table-row-hover group"
    onClick={() => onRecordClick(record)}  // fires setSelectedRecord(record) in App.jsx
  >
    <td>{record.uid}</td>
    <td>{record.surveyor_name}</td>
    <td>{record.survey_date}</td>
    <td>{formatDuration(record.time_difference_seconds)}</td>
    <td>
      <span className={`badge badge-${record.fraud_type}`}>
        {FRAUD_EMOJI[record.fraud_type]} {FRAUD_LABELS[record.fraud_type]}
      </span>
    </td>
    <td>
      <span className={`${getScoreColor(record.quality_score)} ${getScoreBg(record.quality_score)}`}>
        {record.quality_score?.toFixed(1)}/10
      </span>
    </td>
  </tr>
))
```

## 4.2 RecordDetail Opens (RecordDetail.jsx)

The record object from the table row already has `detailed_analysis` embedded (came from `to_dict()`).

```jsx
// RecordDetail.jsx — extract analysis data
const analysis = record.detailed_analysis || null;
const sections = analysis?.section_analysis || [];           // 5 section objects
const executiveSummary = analysis?.executive_summary || record.fraud_reason || '';
const keyFlags = analysis?.key_flags || [];
```

## 4.3 Rendering the Section Cards (RecordDetail.jsx)

```jsx
// RecordDetail.jsx — SectionCard component
function SectionCard({ section }) {
  const [expanded, setExpanded] = useState(false);

  const icon = SECTION_ICONS[section.section] || '📊';
  // SECTION_ICONS = {
  //   'Voice & Speaker Analysis': '🎙️',
  //   'Script Compliance': '📋',
  //   'Data Integrity': '🔍',
  //   'Questioning Technique': '❓',
  //   'Response Authenticity': '🛡️',
  // }

  const verdictStyle = VERDICT_STYLES[section.verdict];
  // VERDICT_STYLES = {
  //   pass:    { bg: 'bg-emerald-100', text: 'text-emerald-800', label: '✅ Pass' },
  //   partial: { bg: 'bg-amber-100',   text: 'text-amber-800',   label: '⚠️ Partial' },
  //   fail:    { bg: 'bg-red-100',     text: 'text-red-800',     label: '❌ Fail' },
  // }

  const scorePercent = (section.score / 10) * 100;
  const scoreBarColor = section.score >= 7 ? 'bg-emerald-500'
                      : section.score >= 5 ? 'bg-amber-500'
                      : 'bg-red-500';

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button onClick={() => setExpanded(!expanded)} className="w-full px-4 py-3.5 flex items-center gap-3">
        <span>{icon}</span>
        <div className="flex-1">
          <span className="font-semibold">{section.section}</span>
          <span className={`verdict badge ${verdictStyle.bg} ${verdictStyle.text}`}>
            {verdictStyle.label}
          </span>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full">
              <div className={`h-full ${scoreBarColor}`} style={{ width: `${scorePercent}%` }} />
            </div>
            <span>{section.score?.toFixed(1)}</span>
          </div>
        </div>
        <svg className={expanded ? 'rotate-180' : ''}>{/* chevron icon */}</svg>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-gray-100">
          {/* Findings (bullet points) */}
          <ul>
            {section.findings.map((finding, idx) => (
              <li key={idx}>{finding}</li>
            ))}
          </ul>

          {/* Evidence (severity-coded cards) */}
          {section.evidence.map((ev, idx) => {
            const sev = SEVERITY_STYLES[ev.severity];
            // SEVERITY_STYLES = {
            //   critical: { bg: 'bg-red-100',  text: 'text-red-800',   label: '🔴 Critical' },
            //   warning:  { bg: 'bg-amber-100', text: 'text-amber-800', label: '🟡 Warning' },
            //   info:     { bg: 'bg-blue-50',   text: 'text-blue-700',  label: '🔵 Info' },
            // }
            return (
              <div key={idx} className={`${sev.bg} border rounded-lg p-3`}>
                <span>{sev.label}</span>
                <span>[{ev.type}]</span>  {/* e.g. [transcript], [mismatch], [metadata] */}
                <p>{ev.text}</p>          {/* specific evidence text from LLM */}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

---

# FLOW 5: Re-Analyze (User Selects Different Model)

```
User selects model dropdown → clicks Re-Analyze button
        │
        ▼
RecordDetail.jsx:handleReanalyze()
        │  POST /api/records/{uid}/reanalyze?model=llama-3.3-70b-versatile
        ▼
main.py:reanalyze_record()
        │  1. Load existing record from DB (transcript already stored)
        │  2. Call fraud_detection.analyze_fraud() with NEW model
        │  3. Build detailed_analysis JSON
        │  4. Update ALL score + analysis columns in DB
        │  5. Return updated record.to_dict()
        ▼
RecordDetail.jsx:setRecord(result.record)
        └─► UI re-renders with new section cards + evidence
```

## 5.1 Frontend (RecordDetail.jsx)

```jsx
const handleReanalyze = async () => {
  setIsReanalyzing(true);
  setReanalyzeStatus(`🤖 Re-analyzing with ${models.find(m => m.id === selectedModel)?.name}...`);

  try {
    const result = await api.reanalyzeRecord(record.uid, selectedModel);
    setRecord(result.record);                           // updates THIS panel with new analysis
    setReanalyzeStatus('✅ Done! Scroll down for detailed analysis.');
    if (onRecordUpdate) onRecordUpdate(result.record); // refreshes dashboard table row too
  } catch (err) {
    setReanalyzeStatus(`❌ Failed: ${err.message}`);
  } finally {
    setIsReanalyzing(false);
  }
};
```

## 5.2 Backend Re-Analyze Endpoint (main.py)

```python
# main.py — POST /api/records/{uid}/reanalyze
@app.post("/api/records/{uid}/reanalyze")
def reanalyze_record(
    uid: int,
    model: str = Query(DEFAULT_MODEL),
    db: Session = Depends(get_db),
):
    record = db.query(AuditRecord).filter(AuditRecord.uid == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record with UID {uid} not found")

    # Reuse stored transcript (no re-transcription — saves time + API cost)
    transcript = record.transcript or ""
    raw_data = json.loads(record.raw_json) if record.raw_json else {}
    audio_answers = raw_data.get("audioanswers", [])
    movement = str(raw_data.get("movement", "0"))

    # Re-run ONLY the LLM analysis with the selected model
    result = analyze_fraud(
        uid=uid,
        surveyor=record.surveyor_name or "",
        date=record.survey_date or "",
        time=record.survey_time or "",
        duration=record.time_difference_seconds or 0,
        registered_gender=record.respondent_gender or "",
        dob=record.respondent_dob or "",
        address=record.actual_address or "",
        movement=movement,
        answers=audio_answers,
        transcript=transcript,
        model=model,
    )

    detailed = {
        "executive_summary": result.get("executive_summary", ""),
        "section_analysis": result.get("section_analysis", []),
        "key_flags": result.get("key_flags", []),
    }

    record.fraud_detected = result.get("fraud_detected", False)
    record.fraud_type = result.get("fraud_type", "clean")
    record.fraud_reason = result.get("executive_summary", "")
    record.quality_score = result.get("quality_score", 5.0)
    record.completeness_score = result.get("completeness_score", 5.0)
    record.fraud_risk_score = result.get("fraud_risk_score", 5.0)
    record.technique_score = result.get("technique_score", 5.0)
    record.detailed_analysis = json.dumps(detailed, ensure_ascii=False)
    db.commit()
    db.refresh(record)

    return {
        "message": f"Re-analyzed UID {uid} with model {model}",
        "model_used": model,
        "record": record.to_dict(),   # full record sent back to frontend
        "analysis": result,
    }
```

---

# FLOW 6: Upload New Audio File

```
User uploads audio + selects model in UploadModal
        │  POST /api/upload-audio (multipart/form-data)
        │  body: metadata (JSON string) + audio_file (.wav)
        ▼
main.py:upload_audio()
        │  1. Save .wav to backend/uploads/{uid}.wav
        │  2. transcription.py:transcribe_audio(path)   → Groq Whisper
        │  3. fraud_detection.py:analyze_fraud(...)      → Groq LLaMA
        │  4. Build detailed_analysis JSON
        │  5. Save AuditRecord to DB
        │  6. Return record.to_dict()
        ▼
Frontend refreshAll() → re-fetches stats + records
```

---

# FLOW 7: Startup Database Migration

When `python main.py` (or `uvicorn main:app`) starts, it auto-migrates the existing SQLite DB to add the new `detailed_analysis` column:

```python
# main.py — startup event
@app.on_event("startup")
def startup():
    init_db()    # Creates tables if they don't exist (CREATE TABLE IF NOT EXISTS)
    from sqlalchemy import text, inspect
    try:
        insp = inspect(engine)
        columns = [col['name'] for col in insp.get_columns('audit_records')]
        if 'detailed_analysis' not in columns:
            # ALTER TABLE — add column to existing DB without data loss
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE audit_records ADD COLUMN detailed_analysis TEXT"))
                conn.commit()
            print("[Migration] Added 'detailed_analysis' column to audit_records")
        else:
            print("[Migration] 'detailed_analysis' column already exists")
    except Exception as e:
        print(f"[Migration] Note: {e}")
```

---

# Available LLM Models

```python
# fraud_detection.py
AVAILABLE_MODELS = {
    "llama-3.3-70b-versatile": "LLaMA 3.3 70B (Best quality, slower)",
    "llama-3.1-8b-instant":    "LLaMA 3.1 8B (Fast, good quality)",
    "llama3-70b-8192":         "LLaMA 3 70B (High quality)",
    "llama3-8b-8192":          "LLaMA 3 8B (Fastest)",
    "mixtral-8x7b-32768":      "Mixtral 8x7B (Balanced)",
    "gemma2-9b-it":            "Gemma 2 9B (Google)",
}

DEFAULT_MODEL = "llama-3.3-70b-versatile"
```

Users can select the model from:
1. The **header dropdown** in the app (used for new uploads)
2. The **Re-Analyze dropdown** inside each record's detail panel

---

# Scoring Rubric

| Score Field | What it Measures | How Calculated |
|---|---|---|
| `quality_score` | Overall survey quality | Weighted avg: Voice 25%, Script 20%, Data 20%, Technique 15%, Authenticity 20% |
| `completeness_score` | % of questions answered | Script Compliance section score |
| `fraud_risk_score` | Likelihood of fraud | Evidence weight (critical=high risk) — higher = more suspicious |
| `technique_score` | Quality of questioning | Questioning Technique section score |

**Section verdict thresholds:**
- `pass` → score ≥ 7.0  
- `partial` → score 4.0–6.9  
- `fail` → score < 4.0  

**Evidence severity levels:**
- `critical` 🔴 → Hard evidence of fraud (gender mismatch, single voice, fake timestamps, contradictions)
- `warning` 🟡 → Suspicious patterns (short duration, no natural pauses, leading questions)
- `info` 🔵 → Notable observations (not necessarily bad, just worth noting)

**Duration interpretation (from prompt instructions):**
- `< 300s` → Very suspicious
- `300–600s` → Short
- `600–1200s` → Normal
- `> 1200s` → Thorough

---

# FLOW 8: Speaker Diarization Pipeline (pyannote GPU)

## 8.1 Overview

Before the LLM analyzes the transcript, the audio file is sent through **pyannote/speaker-diarization-3.1** running locally on GPU. This detects:
- How many distinct speakers are in the recording
- How much each speaker talks (% of speaking time)
- How many speaker turns (back-and-forth exchanges)
- Average turn duration

This data is then injected into the LLM prompt as **hard evidence** — not guessed from text.

```
audio.wav → pyannote (GPU) → {num_speakers: 2, SPEAKER_00: 45%, SPEAKER_01: 55%, 28 turns}
                                    |
                                    ▼
                         fraud_detection.py prompt
                         {speaker_analysis} = formatted speaker data
                                    |
                                    ▼
                         LLM uses it in Voice & Speaker Analysis section
```

## 8.2 Speaker Analysis Code (speaker_analysis.py)

```python
# speaker_analysis.py — lazy-loaded pyannote pipeline
import os
import soundfile as sf
import torch
from pyannote.audio import Pipeline

_pipeline = None  # loaded once, reused

def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    # Read token at call time (after main.py has called load_dotenv)
    hf_token = os.getenv("HF_TOKEN", "")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,       # from .env (v4 API: `token`, not `use_auth_token`)
    )
    _pipeline = _pipeline.to(device)  # GPU acceleration
    return _pipeline


def analyze_speakers(audio_file_path: str) -> dict:
    pipeline = _get_pipeline()

    # Pre-load audio with soundfile (bypasses broken torchcodec on Windows)
    audio_np, sample_rate = sf.read(audio_file_path, dtype="float32")
    if audio_np.ndim == 1:
        waveform = torch.from_numpy(audio_np).unsqueeze(0)
    else:
        waveform = torch.from_numpy(audio_np.T)

    # Run diarization on GPU with pre-loaded waveform
    diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

    # pyannote 4.x returns DiarizeOutput — extract the Annotation
    if hasattr(diarization, 'speaker_diarization'):
        annotation = diarization.speaker_diarization
    else:
        annotation = diarization  # fallback for older versions

    speakers = {}
    timeline = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        # turn.start, turn.end = timestamps in seconds
        # speaker = "SPEAKER_00", "SPEAKER_01", etc.
        if speaker not in speakers:
            speakers[speaker] = {"total_time": 0.0, "segments": 0}
        speakers[speaker]["total_time"] += (turn.end - turn.start)
        speakers[speaker]["segments"] += 1
        timeline.append({"speaker": speaker, "start": turn.start, "end": turn.end})

    return {
        "num_speakers": len(speakers),
        "speakers": speakers,         # per-speaker breakdown
        "speaker_turns": len(timeline),
        "total_duration": max(t["end"] for t in timeline),
        "timeline": timeline[:50],    # First 50 turns for prompt + frontend display
    }
```

### Key Design Decisions (pyannote 4.0.4 + PyTorch 2.6 + Windows):
- **`soundfile` for audio loading**: `torchcodec` (pyannote 4.x default) is incompatible with PyTorch 2.6 on Windows. `torchaudio` also fails without FFmpeg. `soundfile` works natively.
- **`token=` not `use_auth_token=`**: pyannote 4.x changed the API argument name.
- **`DiarizeOutput` wrapper**: pyannote 4.x returns `DiarizeOutput` instead of raw `Annotation`. Access via `.speaker_diarization`.
- **Lazy token reading**: `HF_TOKEN` is read inside `_get_pipeline()` (at call time) rather than at import time, ensuring `load_dotenv()` has already run.

## 8.3 Speaker Data Caching

Speaker diarization is expensive (~53s on RTX 4050 for a 15-minute audio). To avoid re-running the GPU pipeline on every re-analysis:

```python
# models.py — AuditRecord
speaker_data = Column(Text)  # JSON: cached pyannote diarization result

# main.py — reanalyze_record endpoint
# Check for cached speaker data first
cached_speaker = json.loads(record.speaker_data) if record.speaker_data else None
if cached_speaker and not cached_speaker.get("error"):
    speaker_data = cached_speaker   # instant — skip GPU
    print("[Re-Analyze] Using CACHED speaker data")
else:
    speaker_data = analyze_speakers(audio_path)  # ~53s on GPU
    record.speaker_data = json.dumps(speaker_data)  # cache for next time
```

**Flow:**
1. **First analysis** (upload or first re-analyze): Runs GPU → stores result in `speaker_data` column
2. **Subsequent re-analyzes**: Loads cached data instantly → re-runs only LLM analysis

## 8.4 Timestamp-Linked Evidence Clips

The LLM prompt instructs the model to include `timestamp_start` and `timestamp_end` in evidence items:

```json
{
  "type": "diarization",
  "text": "Only 1 speaker detected throughout — strong indicator of mimicry",
  "severity": "critical",
  "timestamp_start": 45.0,
  "timestamp_end": 52.0
}
```

**Frontend (RecordDetail.jsx):** Evidence items with timestamps show a **▶ Play Clip** button that:
1. Seeks the HTML5 `<audio>` element to `timestamp_start`
2. Plays for `(timestamp_end - timestamp_start)` seconds
3. Auto-pauses when the clip ends

```jsx
const playClip = (startSeconds, endSeconds) => {
    const audio = audioRef.current;
    audio.currentTime = startSeconds;
    audio.play();
    setTimeout(() => audio.pause(), (endSeconds - startSeconds) * 1000 + 200);
};
```

## 8.5 Speaker Timeline Visualization

The `SpeakerTimelineBar` component renders a color-coded bar showing who spoke when:

```
Conversation Timeline
┌─────────────────────────────────────────────────────────────┐
│ ██  ████   ███████   ██   ████████   ██  ████  ███████████ │
│ Blue=Surveyor         Green=Respondent                      │
└─────────────────────────────────────────────────────────────┘
                                          Click timeline to play
```

- **Blue** segments = SPEAKER_00 (Surveyor)
- **Green** segments = SPEAKER_01 (Respondent)
- **Clickable**: Click anywhere on the bar to play audio from that point
- Shows speaker turns as proportional colored blocks

## 8.6 How Speaker Data Flows into the LLM Prompt

`format_speaker_data_for_prompt()` converts the dict into text like:
```
SPEAKER ANALYSIS (pyannote AI diarization — machine-detected, not guessed):
  Speakers detected: 2
  Total audio duration: 786.3s
  Total speaker turns: 28
  Average turn duration: 28.1s

  SPEAKER_00: spoke for 354.1s (45.0% of speaking time), 14 segments
  SPEAKER_01: spoke for 432.2s (55.0% of speaking time), 14 segments

  ✅ TWO speakers detected — consistent with a real surveyor-respondent interview.

  First 10 speaker turns:
    Turn 1: SPEAKER_00 [0.0s – 5.2s] (5.2s)
    Turn 2: SPEAKER_01 [5.5s – 12.8s] (7.3s)
    ...
```

This block replaces `{speaker_analysis}` in the LLM prompt template.

## 8.7 Frontend Display (RecordDetail.jsx)

The `SpeakerDiarizationCard` component renders:
- **Status banner**: 🔴 "Only 1 speaker" or ✅ "2 speakers detected"
- **Per-speaker progress bars**: shows time and percentage for each speaker
- **Stats**: total speakers, turns, avg turn duration
- **Timeline bar**: clickable color-coded visualization of the conversation
- Speaker data source: prefers `record.speaker_data` (cached), falls back to `analysis.speaker_data`

## 8.8 Test Endpoint (main.py)

```python
# POST /api/test-speaker-analysis
@app.post("/api/test-speaker-analysis")
def test_speaker_analysis():
    # Returns:
    # - gpu_available: true/false
    # - gpu_name: "NVIDIA GeForce RTX 4050 Laptop GPU" etc.
    # - torch_version, cuda_version
    # - pipeline_loaded: true/false
    # - test_audio: filename of test .wav
    # - diarization_result: {num_speakers, speakers, turns}
    # - time_seconds: how long it took
    # - error: null or error message
```

Frontend has a **🔊 Test GPU** button in the header that calls this endpoint and shows a diagnostic modal.

---

# How to Run

```bash
# 1. Set API keys
# In C:\Path\To\Project\zaudi-mvp\backend\.env:
GROQ_API_KEY=your_groq_key_here
HF_TOKEN=your_huggingface_token_here

# 2. Accept pyannote model terms (one-time, click "Agree" on each page):
#    https://huggingface.co/pyannote/speaker-diarization-3.1
#    https://huggingface.co/pyannote/segmentation-3.0
#    https://huggingface.co/pyannote/speaker-diarization-community-1

# 3. Install backend dependencies
cd "C:\Path\To\Project\zaudi-mvp\backend"
pip install fastapi uvicorn sqlalchemy groq python-dotenv pandas openpyxl soundfile

# 4. Install GPU-enabled PyTorch + pyannote (IMPORTANT: use CUDA index URL)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install pyannote.audio

# 5. (Optional) Seed database with live AI — takes ~5-10 min for 9 records
python seed_real.py

# 6. Start backend (migration runs automatically on first startup)
python -m uvicorn main:app --reload --port 8000

# 7. Start frontend (new terminal)
cd "C:\Path\To\Project\zaudi-mvp\frontend"
npm install
npm run dev

# 8. Open browser
http://localhost:5173

# 9. Test speaker diarization: click "🔊 Test GPU" button in header
```

