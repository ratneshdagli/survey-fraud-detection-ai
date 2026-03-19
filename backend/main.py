"""
Z-AUDIT — FastAPI Backend
Main application with all REST API endpoints for the audit system.
"""

import os
import json
import shutil
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
from openpyxl import Workbook
from dotenv import load_dotenv

# Load environment variables BEFORE importing local modules
# (fraud_detection.py reads GROQ_API_KEY at import time)
load_dotenv()

from models import init_db, get_db, AuditRecord, engine
from transcription import transcribe_audio, mock_transcript_from_answers
from fraud_detection import analyze_fraud, AVAILABLE_MODELS, DEFAULT_MODEL
from speaker_analysis import analyze_speakers

# Create uploads directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Audio files directory (original recordings)
AUDIO_DIR = os.getenv("AUDIO_DIR", r"d:\Zeex AI\MH Project 17-03-26")

# Initialize FastAPI
app = FastAPI(
    title="Z-AUDIT API",
    description="AI-powered audio quality auditing system for field survey calls",
    version="1.0.0",
)

# CORS — allow frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialize database on startup and run migrations."""
    init_db()
    # Migration: add detailed_analysis column if it doesn't exist (for existing DBs)
    from sqlalchemy import text, inspect
    try:
        insp = inspect(engine)
        columns = [col['name'] for col in insp.get_columns('audit_records')]
        if 'detailed_analysis' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE audit_records ADD COLUMN detailed_analysis TEXT"))
                conn.commit()
            print("[Migration] Added 'detailed_analysis' column to audit_records")
        else:
            print("[Migration] 'detailed_analysis' column already exists")
        # Migration: add speaker_data column for caching diarization results
        if 'speaker_data' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE audit_records ADD COLUMN speaker_data TEXT"))
                conn.commit()
            print("[Migration] Added 'speaker_data' column to audit_records")
        else:
            print("[Migration] 'speaker_data' column already exists")
    except Exception as e:
        print(f"[Migration] Note: {e}")


# ============================
# Root route
# ============================

@app.get("/")
def root():
    return {
        "name": "Z-AUDIT API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": ["/api/stats", "/api/records", "/api/upload-audio", "/api/upload-batch", "/api/export/excel", "/api/models"],
    }


# ============================
# Health check
# ============================

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/test-speaker-analysis")
def test_speaker_analysis(db: Session = Depends(get_db)):
    """Test the speaker diarization pipeline — checks GPU, model loading, and runs on a sample audio."""
    import time
    import torch

    result = {
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
        "pipeline_loaded": False,
        "test_audio": None,
        "diarization_result": None,
        "time_seconds": None,
        "error": None,
    }

    # Find a test audio file
    test_audio = None
    # Try AUDIO_DIR first
    if os.path.exists(AUDIO_DIR):
        for f in os.listdir(AUDIO_DIR):
            if f.endswith(".wav"):
                test_audio = os.path.join(AUDIO_DIR, f)
                break

    # Fallback to uploads dir
    if not test_audio and os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f.endswith(".wav"):
                test_audio = os.path.join(UPLOAD_DIR, f)
                break

    if not test_audio:
        result["error"] = "No .wav audio files found to test with"
        return result

    result["test_audio"] = os.path.basename(test_audio)
    result["test_audio_size_mb"] = round(os.path.getsize(test_audio) / (1024 * 1024), 1)

    try:
        start = time.time()
        speaker_data = analyze_speakers(test_audio)
        elapsed = round(time.time() - start, 2)

        result["pipeline_loaded"] = True
        result["time_seconds"] = elapsed
        result["diarization_result"] = {
            "num_speakers": speaker_data.get("num_speakers"),
            "speakers": speaker_data.get("speakers", {}),
            "speaker_turns": speaker_data.get("speaker_turns", 0),
            "total_duration": speaker_data.get("total_duration", 0),
            "analysis_source": speaker_data.get("analysis_source", ""),
        }
        if speaker_data.get("error"):
            result["error"] = speaker_data["error"]
            result["pipeline_loaded"] = False

    except Exception as e:
        result["error"] = str(e)
        result["time_seconds"] = round(time.time() - start, 2)

    return result


# ============================
# Serve Audio Files
# ============================

@app.get("/api/audio/{uid}")
def get_audio(uid: int):
    """Serve the original audio file for a given UID."""
    audio_path = os.path.join(AUDIO_DIR, f"{uid}.wav")
    if not os.path.exists(audio_path):
        # Try uploads dir
        audio_path = os.path.join(UPLOAD_DIR, f"{uid}.wav")
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file for UID {uid} not found")
    return FileResponse(audio_path, media_type="audio/wav", filename=f"{uid}.wav")


# ============================
# Dashboard Stats
# ============================

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Dashboard statistics — total, fraud counts by type, avg scores."""
    total = db.query(func.count(AuditRecord.id)).scalar() or 0
    fraud_count = db.query(func.count(AuditRecord.id)).filter(AuditRecord.fraud_detected == True).scalar() or 0
    clean_count = total - fraud_count
    avg_quality = db.query(func.avg(AuditRecord.quality_score)).scalar() or 0.0

    # Fraud breakdown by type
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


# ============================
# Agent Leaderboard
# ============================

@app.get("/api/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    """Rank agents by fraud risk and count."""
    from sqlalchemy import func, case
    
    # Query aggregated stats per surveyor
    results = db.query(
        AuditRecord.surveyor_name,
        func.count(AuditRecord.id).label("total_calls"),
        func.sum(case((AuditRecord.fraud_detected == True, 1), else_=0)).label("fraud_calls"),
        func.avg(AuditRecord.fraud_risk_score).label("avg_risk_score")
    ).filter(
        AuditRecord.surveyor_name.isnot(None)
    ).group_by(
        AuditRecord.surveyor_name
    ).all()

    leaderboard = []
    for r in results:
        name = r.surveyor_name
        total = int(r.total_calls or 0)
        fraud = int(r.fraud_calls or 0)
        risk = float(r.avg_risk_score or 0)
        
        if total > 0:
            rate = (fraud / total) * 100
            # Composite score (higher is worse): 60% rate + 40% risk score
            composite = (rate * 6.0) + (risk * 0.4)
            composite = min(10.0, max(0.0, composite))
            
            leaderboard.append({
                "surveyor_name": name,
                "total_calls": total,
                "fraud_calls": fraud,
                "fraud_rate": round(rate, 1),
                "avg_risk_score": round(risk, 1),
                "composite_risk_score": round(composite, 1)
            })
            
    # Sort by worst risk first
    leaderboard.sort(key=lambda x: x["composite_risk_score"], reverse=True)
    return leaderboard


# ============================
# Cross-Call Heatmap
# ============================

@app.get("/api/heatmap")
def get_heatmap(db: Session = Depends(get_db)):
    """Generate calendar heatmap data for fraud occurrence over time."""
    from sqlalchemy import func, case

    # Group by survey_date
    results = db.query(
        AuditRecord.survey_date,
        func.count(AuditRecord.id).label("total"),
        func.sum(case((AuditRecord.fraud_detected == True, 1), else_=0)).label("fraud")
    ).filter(
        AuditRecord.survey_date.isnot(None)
    ).group_by(
        AuditRecord.survey_date
    ).all()

    heatmap = []
    for r in results:
        total = int(r.total or 0)
        fraud = int(r.fraud or 0)
        if total > 0:
            heatmap.append({
                "date": r.survey_date,
                "total_calls": total,
                "fraud_calls": fraud,
                "fraud_rate": round((fraud / total) * 100, 1)
            })

    return heatmap


# ============================
# List Records (with filters + pagination)
# ============================

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
    """List audit records with filters and pagination."""
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
        # Check if search is numeric (UID search)
        if search.isdigit():
            query = query.filter(AuditRecord.uid == int(search))
        else:
            query = query.filter(AuditRecord.surveyor_name.like(search_term))

    # Get total before pagination
    total = query.count()
    
    # Order and paginate
    records = query.order_by(AuditRecord.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "records": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
    }


# ============================
# Get Single Record
# ============================

@app.get("/api/records/{uid}")
def get_record(uid: int, db: Session = Depends(get_db)):
    """Get a single audit record by UID."""
    record = db.query(AuditRecord).filter(AuditRecord.uid == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record with UID {uid} not found")
    return record.to_dict()


# ============================
# Delete Record
# ============================

@app.delete("/api/records/{uid}")
def delete_record(uid: int, db: Session = Depends(get_db)):
    """Delete an audit record by UID."""
    record = db.query(AuditRecord).filter(AuditRecord.uid == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record with UID {uid} not found")
    db.delete(record)
    db.commit()
    return {"message": f"Record {uid} deleted successfully"}


# ============================
# Re-Analyze Record (LLM only — reuse existing transcript)
# ============================

@app.post("/api/records/{uid}/reanalyze")
def reanalyze_record(
    uid: int,
    model: str = Query(DEFAULT_MODEL),
    db: Session = Depends(get_db),
):
    """
    Re-run ONLY the LLM fraud analysis on an existing record.
    Reuses the stored transcript — does NOT re-run Whisper transcription.
    Allows switching between models (8B, 70B, Mixtral, etc.)
    """
    record = db.query(AuditRecord).filter(AuditRecord.uid == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record with UID {uid} not found")

    # Get existing data
    transcript = record.transcript or ""
    raw_data = {}
    try:
        raw_data = json.loads(record.raw_json) if record.raw_json else {}
    except:
        pass

    audio_answers = raw_data.get("audioanswers", [])
    movement = str(raw_data.get("movement", "0"))

    # Check for cached speaker data first (avoid re-running 53s GPU pipeline)
    cached_speaker = None
    if record.speaker_data:
        try:
            cached_speaker = json.loads(record.speaker_data)
            if cached_speaker and not cached_speaker.get("error"):
                print(f"[Re-Analyze] Using CACHED speaker data for UID {uid} — {cached_speaker.get('num_speakers')} speaker(s)")
        except:
            cached_speaker = None

    if cached_speaker and not cached_speaker.get("error"):
        speaker_data = cached_speaker
    else:
        # No cached data — run GPU diarization
        audio_path = os.path.join(AUDIO_DIR, f"{uid}.wav")
        speaker_data = analyze_speakers(audio_path)
        print(f"[Re-Analyze] Fresh speaker analysis for UID {uid}: {speaker_data.get('num_speakers')} speaker(s)")
        # Cache it for next time
        if not speaker_data.get("error"):
            record.speaker_data = json.dumps(speaker_data, ensure_ascii=False)

    # Re-run fraud analysis with the selected model + real speaker data
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
        speaker_data=speaker_data,
        db=db,
        surveyor_id=record.surveyor_id,
    )

    # Build the detailed analysis JSON
    detailed = {
        "executive_summary": result.get("executive_summary", result.get("fraud_reason", "")),
        "section_analysis": result.get("section_analysis", []),
        "key_flags": result.get("key_flags", []),
        "speaker_data": speaker_data if not speaker_data.get("error") else None,
    }

    # Update the record with new analysis
    record.fraud_detected = result.get("fraud_detected", False)
    record.fraud_type = result.get("fraud_type", "clean")
    record.fraud_reason = result.get("executive_summary", result.get("fraud_reason", ""))
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
        "record": record.to_dict(),
        "analysis": result,
    }


# ============================
# Upload Single Audio + Metadata
# ============================

@app.post("/api/upload-audio")
async def upload_audio(
    metadata: str = Form(...),
    model: str = Form(DEFAULT_MODEL),
    audio_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Upload a single audio file + JSON metadata, run the full audit pipeline.
    If no audio file, uses mock transcript from audioanswers.
    """
    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON metadata")

    uid = meta.get("id1") or meta.get("uid")
    if not uid:
        raise HTTPException(status_code=400, detail="Missing UID in metadata")

    # Check if record already exists
    existing = db.query(AuditRecord).filter(AuditRecord.uid == uid).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Record with UID {uid} already exists")

    # Extract metadata fields
    surveyor = meta.get("surveyor", "Unknown")
    date = meta.get("date", "")
    time_val = meta.get("time", "")
    duration_str = meta.get("timedifference", "0")
    duration = int("".join(filter(str.isdigit, str(duration_str)))) if duration_str else 0
    movement = str(meta.get("movement", "0"))
    address = meta.get("actualaddress", "")
    audio_answers = meta.get("audioanswers", [])

    # Registration details
    reg_details = meta.get("registration_details", [])
    gender = ""
    dob = ""
    area = ""
    occupation = ""
    for detail in reg_details:
        if isinstance(detail, list) and len(detail) >= 2:
            if detail[1] == "GENDER":
                gender = detail[0]
            elif detail[1] == "DOB":
                dob = detail[0]
            elif detail[1] == "AREA":
                area = detail[0]
            elif detail[1] == "OCCUPATION":
                occupation = detail[0]

    # Step 1: Transcription
    transcript = ""
    audio_path = ""
    if audio_file:
        # Save uploaded audio
        audio_path = os.path.join(UPLOAD_DIR, f"{uid}.wav")
        with open(audio_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        transcript = transcribe_audio(audio_path)

    # Fallback to mock transcript
    if not transcript:
        transcript = mock_transcript_from_answers(audio_answers)

    # Step 1.5: Speaker Diarization
    speaker_data = analyze_speakers(audio_path) if audio_path else {"error": "No audio file"}

    # Step 2: Fraud Analysis (with real speaker data)
    result = analyze_fraud(
        uid=uid,
        surveyor=surveyor,
        date=date,
        time=time_val,
        duration=duration,
        registered_gender=gender,
        dob=dob,
        address=address,
        movement=movement,
        answers=audio_answers,
        transcript=transcript,
        model=model,
        speaker_data=speaker_data,
    )

    # Build the detailed analysis JSON
    detailed = {
        "executive_summary": result.get("executive_summary", result.get("fraud_reason", "")),
        "section_analysis": result.get("section_analysis", []),
        "key_flags": result.get("key_flags", []),
        "speaker_data": speaker_data if not speaker_data.get("error") else None,
    }

    # Step 3: Save to database
    record = AuditRecord(
        uid=uid,
        surveyor_name=surveyor,
        surveyor_id=meta.get("tldetails", ""),
        survey_date=date,
        survey_time=time_val,
        time_difference_seconds=duration,
        actual_address=address,
        respondent_gender=gender,
        respondent_dob=dob,
        respondent_area=area,
        respondent_occupation=occupation,
        audio_url=audio_path or str(meta.get("audiourls", "")),
        transcript=transcript,
        fraud_detected=result.get("fraud_detected", False),
        fraud_type=result.get("fraud_type", "clean"),
        fraud_reason=result.get("executive_summary", result.get("fraud_reason", "")),
        quality_score=result.get("quality_score", 5.0),
        completeness_score=result.get("completeness_score", 5.0),
        fraud_risk_score=result.get("fraud_risk_score", 5.0),
        technique_score=result.get("technique_score", 5.0),
        detailed_analysis=json.dumps(detailed, ensure_ascii=False),
        speaker_data=json.dumps(speaker_data, ensure_ascii=False) if not speaker_data.get("error") else None,
        raw_json=json.dumps(meta, ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "Audit completed successfully",
        "record": record.to_dict(),
        "analysis": result,
    }


# ============================
# Batch Upload (Excel/CSV)
# ============================

@app.post("/api/upload-batch")
async def upload_batch(
    file: UploadFile = File(...),
    model: str = Form(DEFAULT_MODEL),
    db: Session = Depends(get_db),
):
    """Upload an Excel or CSV file and process all rows."""
    # Save file temporarily
    suffix = ".xlsx" if "xlsx" in file.filename else ".csv"
    tmp_path = os.path.join(tempfile.gettempdir(), f"zaudi_batch{suffix}")
    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        # Read the file
        if suffix == ".xlsx":
            df = pd.read_excel(tmp_path)
        else:
            df = pd.read_csv(tmp_path)

        results = []
        errors = []

        for idx, row in df.iterrows():
            try:
                # The CSV has the JSON in the 3rd column (index 2)
                json_str = None
                for col in df.columns:
                    val = str(row[col]) if pd.notna(row[col]) else ""
                    if val.startswith("{") and "surveyor" in val:
                        json_str = val
                        break

                if not json_str:
                    errors.append({"row": idx, "error": "No valid JSON found in row"})
                    continue

                meta = json.loads(json_str)
                uid = meta.get("id1") or meta.get("uid")

                if not uid:
                    errors.append({"row": idx, "error": "No UID found"})
                    continue

                # Check if exists
                existing = db.query(AuditRecord).filter(AuditRecord.uid == uid).first()
                if existing:
                    errors.append({"row": idx, "uid": uid, "error": "Already exists"})
                    continue

                # Extract fields
                surveyor = meta.get("surveyor", "Unknown")
                date = meta.get("date", "")
                time_val = meta.get("time", "")
                duration_str = meta.get("timedifference", "0")
                duration = int("".join(filter(str.isdigit, str(duration_str)))) if duration_str else 0
                movement = str(meta.get("movement", "0"))
                address = meta.get("actualaddress", "")
                audio_answers = meta.get("audioanswers", [])

                reg_details = meta.get("registration_details", [])
                gender, dob, area, occupation = "", "", "", ""
                for detail in reg_details:
                    if isinstance(detail, list) and len(detail) >= 2:
                        if detail[1] == "GENDER": gender = detail[0]
                        elif detail[1] == "DOB": dob = detail[0]
                        elif detail[1] == "AREA": area = detail[0]
                        elif detail[1] == "OCCUPATION": occupation = detail[0]

                # Mock transcript (no audio in batch)
                transcript = mock_transcript_from_answers(audio_answers)

                # Fraud analysis
                result = analyze_fraud(
                    uid=uid, surveyor=surveyor, date=date, time=time_val,
                    duration=duration, registered_gender=gender, dob=dob,
                    address=address, movement=movement, answers=audio_answers,
                    transcript=transcript, model=model,
                )

                # Build detailed analysis JSON
                detailed = {
                    "executive_summary": result.get("executive_summary", result.get("fraud_reason", "")),
                    "section_analysis": result.get("section_analysis", []),
                    "key_flags": result.get("key_flags", []),
                }

                # Save record
                record = AuditRecord(
                    uid=uid, surveyor_name=surveyor,
                    surveyor_id=meta.get("tldetails", ""),
                    survey_date=date, survey_time=time_val,
                    time_difference_seconds=duration,
                    actual_address=address,
                    respondent_gender=gender, respondent_dob=dob,
                    respondent_area=area, respondent_occupation=occupation,
                    audio_url=str(meta.get("audiourls", "")),
                    transcript=transcript,
                    fraud_detected=result.get("fraud_detected", False),
                    fraud_type=result.get("fraud_type", "clean"),
                    fraud_reason=result.get("executive_summary", result.get("fraud_reason", "")),
                    quality_score=result.get("quality_score", 5.0),
                    completeness_score=result.get("completeness_score", 5.0),
                    fraud_risk_score=result.get("fraud_risk_score", 5.0),
                    technique_score=result.get("technique_score", 5.0),
                    detailed_analysis=json.dumps(detailed, ensure_ascii=False),
                    raw_json=json.dumps(meta, ensure_ascii=False),
                )
                db.add(record)
                db.commit()
                results.append({"uid": uid, "status": "success", "fraud_type": result.get("fraud_type")})

            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        return {
            "message": f"Batch processing complete. {len(results)} processed, {len(errors)} errors.",
            "processed": results,
            "errors": errors,
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================
# Export as Excel
# ============================

@app.get("/api/export/excel")
def export_excel(
    fraud_type: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """Export all records as Excel file."""
    query = db.query(AuditRecord)

    if fraud_type and fraud_type != "all":
        query = query.filter(AuditRecord.fraud_type == fraud_type)
    if min_score is not None:
        query = query.filter(AuditRecord.quality_score >= min_score)
    if max_score is not None:
        query = query.filter(AuditRecord.quality_score <= max_score)

    records = query.order_by(AuditRecord.uid).all()

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Z-AUDIT Report"

    # Headers
    headers = [
        "UID", "Surveyor", "Date", "Time", "Duration (s)",
        "Gender", "DOB", "Area", "Occupation", "Address",
        "Fraud Detected", "Fraud Type", "Fraud Reason",
        "Quality Score", "Completeness Score", "Fraud Risk Score", "Technique Score",
    ]
    ws.append(headers)

    for r in records:
        ws.append([
            r.uid, r.surveyor_name, r.survey_date, r.survey_time,
            r.time_difference_seconds, r.respondent_gender, r.respondent_dob,
            r.respondent_area, r.respondent_occupation, r.actual_address,
            "Yes" if r.fraud_detected else "No", r.fraud_type, r.fraud_reason,
            r.quality_score, r.completeness_score, r.fraud_risk_score, r.technique_score,
        ])

    # Save to temp file
    export_path = os.path.join(tempfile.gettempdir(), "zaudi_export.xlsx")
    wb.save(export_path)

    return FileResponse(
        export_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Z-AUDIT_Report.xlsx",
    )


# ============================
# Available Models Endpoint
# ============================

@app.get("/api/models")
def get_available_models():
    """Return list of available LLM models for fraud analysis."""
    return {
        "models": [
            {"id": k, "name": v} for k, v in AVAILABLE_MODELS.items()
        ],
        "default": DEFAULT_MODEL,
    }


# ============================
# Run with: uvicorn main:app --reload --port 8000
# ============================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
