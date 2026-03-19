"""
Z-AUDIT — Database Models
SQLAlchemy models with SQLite backend for audit records.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./zaudi.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uid = Column(Integer, unique=True, nullable=False, index=True)
    surveyor_name = Column(String(200))
    surveyor_id = Column(String(50))
    survey_date = Column(String(50))
    survey_time = Column(String(50))
    time_difference_seconds = Column(Integer)
    actual_address = Column(Text)
    respondent_gender = Column(String(20))
    respondent_dob = Column(String(30))
    respondent_area = Column(String(100))
    respondent_occupation = Column(String(100))
    audio_url = Column(String(500))
    transcript = Column(Text)
    fraud_detected = Column(Boolean, default=False)
    fraud_type = Column(String(100))  # 'fake_form', 'mimicry', 'force_survey', 'clean'
    fraud_reason = Column(Text)
    quality_score = Column(Float)  # 0.0 to 10.0
    completeness_score = Column(Float)
    fraud_risk_score = Column(Float)
    technique_score = Column(Float)
    detailed_analysis = Column(Text)  # JSON: per-section analysis with evidence
    speaker_data = Column(Text)  # JSON: cached pyannote diarization result (avoids re-running GPU)
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_json = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
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
            "detailed_analysis": json.loads(self.detailed_analysis) if self.detailed_analysis else None,
            "speaker_data": json.loads(self.speaker_data) if self.speaker_data else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "raw_json": self.raw_json,
        }


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
