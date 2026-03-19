"""
Z-AUDIT — Audio Transcription Module
Uses Groq Whisper Large v3 for multilingual transcription (Hindi, Marathi, English).
Free tier — no credit card needed.
"""

import os
import json
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe audio using Groq Whisper Large v3.
    Supports multilingual audio (Hindi, Marathi, English, etc.)
    Returns: transcribed text string
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), audio_file.read()),
                model="whisper-large-v3",
                response_format="text",
            )
        return transcription
    except Exception as e:
        print(f"[Transcription Error] {e}")
        return ""


def mock_transcript_from_answers(audio_answers: list) -> str:
    """
    Convert Q&A pairs from the JSON metadata into a readable mock transcript.
    Used when no real audio file is available for demo purposes.
    
    audio_answers format: [[answer, question], [answer, question], ...]
    """
    if not audio_answers:
        return "No transcript available — no audio answers provided."

    lines = ["=== MOCK TRANSCRIPT (Generated from recorded answers) ===\n"]
    q_num = 0

    for pair in audio_answers:
        if not isinstance(pair, list) or len(pair) < 2:
            continue

        answer = pair[0]
        question = pair[1] if len(pair) > 1 else "Unknown question"

        # Skip upload-type questions (Aadhaar, image)
        if question and ("UPLOAD" in str(question).upper()):
            continue

        q_num += 1

        # Clean up the question — extract English portion if multilingual
        q_text = str(question) if question else "Unknown question"
        a_text = str(answer) if answer else "[No answer provided]"

        lines.append(f"Surveyor (Q{q_num}): {q_text[:200]}")
        lines.append(f"Respondent: {a_text[:200]}")
        lines.append("")

    if q_num == 0:
        return "No transcript available — audio answers were empty or invalid."

    lines.append(f"\n=== END OF MOCK TRANSCRIPT ({q_num} questions) ===")
    return "\n".join(lines)
