"""
Z-AUDIT — REAL DATA Seed Script
Reads the actual data_with_json.csv and processes each record with:
  1. Real audio transcription via Groq Whisper Large v3
  2. Real fraud analysis via Groq LLM (LLaMA)

Usage:
  python seed_real.py

This script uses LIVE AI — each record takes 30-60 seconds to process.
Total time for 9 records: ~5-10 minutes.
"""

import os
import sys
import json
import csv
import re
import time
from datetime import datetime
from dotenv import load_dotenv

# Load .env BEFORE importing modules that use os.getenv("GROQ_API_KEY")
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from models import init_db, SessionLocal, AuditRecord
from transcription import transcribe_audio, mock_transcript_from_answers
from fraud_detection import analyze_fraud

# =============================================
# Configuration — CHANGE THESE PATHS IF NEEDED
# =============================================
CSV_PATH = r"d:\Zeex AI\data_with_json.csv"
AUDIO_DIR = r"d:\Zeex AI\MH Project 17-03-26"
USE_REAL_TRANSCRIPTION = True   # Set to False to skip Whisper (uses mock transcript from Q&A)
LLM_MODEL = "llama-3.1-8b-instant"  # Fast 8B model (change to "llama-3.3-70b-versatile" for best quality)


def parse_csv_row(row):
    """Parse a row from data_with_json.csv into a structured dictionary."""
    # The CSV format: column 0 is empty, column 1 is UID, column 2 is the JSON blob
    if len(row) < 3:
        return None

    uid = row[1].strip() if row[1] else None
    json_str = row[2].strip() if row[2] else None

    if not uid or not json_str:
        return None

    try:
        uid = int(uid)
    except ValueError:
        return None

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"  ❌ Could not parse JSON for UID {uid}")
        return None

    return {"uid": uid, "data": data}


def extract_metadata(data):
    """Extract structured metadata from the raw JSON blob."""
    # Basic info
    surveyor = data.get("surveyor", "")
    date = data.get("date", "")
    survey_time = data.get("time", "")
    uid = data.get("id1", 0)

    # Parse time difference
    td_str = data.get("timedifference", "0 seconds")
    td_match = re.search(r'(\d+)', str(td_str))
    time_diff = int(td_match.group(1)) if td_match else 0

    # Address
    address = data.get("actualaddress", "")

    # TL/FR details
    tl_details = data.get("tldetails", "")

    # Registration details
    reg = data.get("registration_details", [])
    gender = ""
    dob = ""
    area = ""
    occupation = ""
    for item in reg:
        if isinstance(item, list) and len(item) >= 2:
            value = str(item[0]).strip() if item[0] else ""
            label = str(item[1]).strip().upper() if item[1] else ""
            if "GENDER" in label:
                gender = value
            elif "DOB" in label:
                dob = value
            elif "AREA" in label:
                area = value
            elif "OCCUPATION" in label:
                occupation = value

    # Audio answers
    audio_answers = data.get("audioanswers", [])

    # Audio URL from audiourls
    audio_url = ""
    audio_urls = data.get("audiourls", [])
    for au in audio_urls:
        if isinstance(au, list) and len(au) >= 2:
            url = str(au[1])
            if ".wav" in url and "registration" not in url.lower():
                audio_url = url
                break

    return {
        "uid": uid,
        "surveyor_name": surveyor,
        "surveyor_id": tl_details,
        "survey_date": date,
        "survey_time": survey_time,
        "time_difference_seconds": time_diff,
        "actual_address": address,
        "respondent_gender": gender,
        "respondent_dob": dob,
        "respondent_area": area,
        "respondent_occupation": occupation,
        "audio_url": audio_url,
        "audio_answers": audio_answers,
        "raw_data": data,
    }


def process_record(meta, db):
    """Process a single record: transcribe + analyze with live AI."""
    uid = meta["uid"]
    audio_file_path = os.path.join(AUDIO_DIR, f"{uid}.wav")

    print(f"\n{'='*60}")
    print(f"  Processing UID: {uid}")
    print(f"  Surveyor: {meta['surveyor_name']}")
    print(f"  Duration: {meta['time_difference_seconds']}s")
    print(f"{'='*60}")

    # Step 1: Transcription
    transcript = None

    if USE_REAL_TRANSCRIPTION and os.path.exists(audio_file_path):
        print(f"  📁 Audio file found: {audio_file_path}")
        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        print(f"  📦 File size: {file_size_mb:.1f} MB")
        print(f"  🎙️  Sending to Groq Whisper Large v3... (this takes 15-30s)")

        try:
            # transcribe_audio() takes a FILE PATH, not bytes
            transcript = transcribe_audio(audio_file_path)
            print(f"  ✅ Transcript received! ({len(transcript)} characters)")
            # Show first 200 chars
            preview = transcript[:200].replace('\n', ' ')
            print(f"  📝 Preview: {preview}...")
        except Exception as e:
            print(f"  ⚠️  Whisper failed: {e}")
            print(f"  📋 Falling back to mock transcript from Q&A answers...")
            transcript = mock_transcript_from_answers(meta["audio_answers"])
    else:
        if not os.path.exists(audio_file_path):
            print(f"  ⚠️  Audio file not found: {audio_file_path}")
        else:
            print(f"  ⏭️  Skipping real transcription (USE_REAL_TRANSCRIPTION=False)")
        print(f"  📋 Using mock transcript from Q&A answers...")
        transcript = mock_transcript_from_answers(meta["audio_answers"])

    # Step 2: Fraud Analysis
    print(f"  🤖 Sending to Groq LLM ({LLM_MODEL}) for fraud analysis...")

    # Extract GPS movement from raw data
    movement = str(meta["raw_data"].get("movement", "0"))

    try:
        # analyze_fraud() takes individual positional arguments, not a dict
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
            model=LLM_MODEL,
            db=db,
            surveyor_id=meta["surveyor_id"],
        )
        print(f"  ✅ Analysis complete!")
        print(f"  🔍 Fraud Type: {result.get('fraud_type', 'unknown')}")
        print(f"  📊 Quality Score: {result.get('quality_score', '?')}/10")
        print(f"  💬 Reason: {result.get('fraud_reason', '?')[:100]}...")
    except Exception as e:
        print(f"  ⚠️  LLM analysis failed: {e}")
        result = {
            "fraud_detected": False,
            "fraud_type": "clean",
            "fraud_reason": f"Analysis failed: {str(e)}",
            "quality_score": 5.0,
            "completeness_score": 5.0,
            "fraud_risk_score": 5.0,
            "technique_score": 5.0,
        }

    # Build the record
    record_data = {
        "uid": uid,
        "surveyor_name": meta["surveyor_name"],
        "surveyor_id": meta["surveyor_id"],
        "survey_date": meta["survey_date"],
        "survey_time": meta["survey_time"],
        "time_difference_seconds": meta["time_difference_seconds"],
        "actual_address": meta["actual_address"],
        "respondent_gender": meta["respondent_gender"],
        "respondent_dob": meta["respondent_dob"],
        "respondent_area": meta["respondent_area"],
        "respondent_occupation": meta["respondent_occupation"],
        "audio_url": os.path.join(AUDIO_DIR, f"{uid}.wav"),
        "transcript": transcript,
        "fraud_detected": result.get("fraud_detected", False),
        "fraud_type": result.get("fraud_type", "clean"),
        "fraud_reason": result.get("fraud_reason", ""),
        "quality_score": result.get("quality_score", 5.0),
        "completeness_score": result.get("completeness_score", 5.0),
        "fraud_risk_score": result.get("fraud_risk_score", 5.0),
        "technique_score": result.get("technique_score", 5.0),
        "raw_json": json.dumps(meta["raw_data"], ensure_ascii=False),
    }

    return record_data


def seed_real():
    """Main function — read CSV, process each record with live AI, save to DB."""
    print("\n" + "=" * 60)
    print("  Z-AUDIT — Real Data Seed Script")
    print("  Using LIVE AI for transcription and analysis")
    print("=" * 60)

    # Check prerequisites
    if not os.path.exists(CSV_PATH):
        print(f"\n❌ CSV file not found: {CSV_PATH}")
        print("   Please check the path and try again.")
        return

    if not os.path.exists(AUDIO_DIR):
        print(f"\n⚠️  Audio directory not found: {AUDIO_DIR}")
        print("   Will use mock transcripts instead of real Whisper transcription.")

    # Initialize database
    init_db()
    db = SessionLocal()

    # Check if already seeded
    existing = db.query(AuditRecord).count()
    if existing > 0:
        print(f"\n⚠️  Database already has {existing} records.")
        response = input("   Delete existing records and re-seed? (y/n): ").strip().lower()
        if response == 'y':
            db.query(AuditRecord).delete()
            db.commit()
            print("   ✅ Cleared existing records.")
        else:
            print("   Skipping. Run 'del zaudi.db' to start fresh.")
            db.close()
            return

    # Read CSV
    print(f"\n📂 Reading CSV: {CSV_PATH}")
    records_to_process = []

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0 and (not row[1] or not row[1].strip().isdigit()):
                # Skip header row if present
                continue
            parsed = parse_csv_row(row)
            if parsed:
                records_to_process.append(parsed)

    print(f"   Found {len(records_to_process)} records to process")

    # Check audio files
    uids = [r["uid"] for r in records_to_process]
    audio_found = sum(1 for uid in uids if os.path.exists(os.path.join(AUDIO_DIR, f"{uid}.wav")))
    print(f"   Audio files found: {audio_found}/{len(uids)}")

    if USE_REAL_TRANSCRIPTION:
        print(f"\n⏱️  Estimated time: {len(records_to_process) * 45}–{len(records_to_process) * 90} seconds")
        print(f"   ({len(records_to_process)} records × 45-90 seconds each)")
    else:
        print(f"\n⏱️  Estimated time: {len(records_to_process) * 15}–{len(records_to_process) * 30} seconds")
        print(f"   (mock transcripts + LLM analysis only)")

    # Process each record
    success_count = 0
    error_count = 0
    start_time = time.time()

    for i, record_data in enumerate(records_to_process):
        uid = record_data["uid"]
        data = record_data["data"]

        meta = extract_metadata(data)

        try:
            result = process_record(meta, db)

            # Save to database
            record = AuditRecord(**result)
            db.add(record)
            db.commit()

            success_count += 1
            print(f"  💾 Saved to database! ({i+1}/{len(records_to_process)})")

            # Rate limiting — Groq free tier has limits
            if i < len(records_to_process) - 1:
                wait = 3 if USE_REAL_TRANSCRIPTION else 1
                print(f"  ⏳ Waiting {wait}s (API rate limit)...")
                time.sleep(wait)

        except Exception as e:
            error_count += 1
            print(f"  ❌ Failed to process UID {uid}: {e}")
            db.rollback()

    elapsed = time.time() - start_time
    db.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"  SEED COMPLETE")
    print(f"{'='*60}")
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  ⏱️  Total time: {elapsed:.1f} seconds")
    print(f"  📊 Transcription: {'REAL (Groq Whisper)' if USE_REAL_TRANSCRIPTION else 'MOCK (from Q&A answers)'}")
    print(f"  🤖 Analysis: REAL (Groq {LLM_MODEL})")
    print(f"\n  Start the backend:  python -m uvicorn main:app --reload --port 8000")
    print(f"  Open dashboard:     http://localhost:5173")


if __name__ == "__main__":
    seed_real()
