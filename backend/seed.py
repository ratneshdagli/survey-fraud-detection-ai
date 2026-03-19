"""
Z-AUDIT — Database Seeder
Pre-populates the database with 9 fraud cases from the QC report for demo purposes.
Run: python seed.py
"""

import json
import sys
import os
from datetime import datetime

# Add parent dir so we can import models
sys.path.insert(0, os.path.dirname(__file__))

from models import init_db, SessionLocal, AuditRecord

SAMPLE_RECORDS = [
    {
        "uid": 111379,
        "surveyor_name": "113145 - (Vansh Patil)",
        "surveyor_id": "26-SACHIN LAVATE",
        "survey_date": "12-Mar-2026",
        "survey_time": "12:22:43",
        "time_difference_seconds": 907,
        "actual_address": "V253+MHM, Shittur Tarf Malkapur, Maharashtra 416213, India",
        "respondent_gender": "Male",
        "respondent_dob": "2007-08-07",
        "respondent_area": "shittur",
        "respondent_occupation": "Student",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\111379.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\n[Background noise, footsteps]\nSurveyor: Gender?\nSurveyor (answering): Male\nSurveyor: Health problems?\nSurveyor (answering): No\n[Wind noise, no second voice detected]\nSurveyor: Where do you go for treatment?\nSurveyor (answering): Government hospitals\n[Call appears to be telephonic, not in-person]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "fake_form",
        "fraud_reason": "Actual respondent is not present face to face. Survey conducted telephonically. Only background noise and surveyor's voice detected — no real respondent interaction. Respondent DOB shows age ~18, registered as Student. The entire call shows no genuine Q&A exchange.",
        "quality_score": 1.5,
        "completeness_score": 3.0,
        "fraud_risk_score": 9.0,
        "technique_score": 2.0,
    },
    {
        "uid": 112136,
        "surveyor_name": "102454 - (Ajinkya Kondvilkar)",
        "surveyor_id": "99-TEST",
        "survey_date": "13-Mar-2026",
        "survey_time": "14:58:15",
        "time_difference_seconds": 532,
        "actual_address": "Sudampuri, Wardha, Maharashtra 442001, India",
        "respondent_gender": "Male",
        "respondent_dob": "1992-03-04",
        "respondent_area": "Mahadevpura",
        "respondent_occupation": "Chef / Cook",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\112136.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\n[Only one voice detected throughout]\nSurveyor: Gender? Male.\nSurveyor: Any health problems? No.\nSurveyor: Where do you go for treatment? Government hospitals.\nSurveyor: Enrolled in schemes? Not enrolled.\nSurveyor: Why not enrolled? Never tried.\nSurveyor: Occupation? Carpenter.\n[Same voice pattern throughout — no pauses for respondent]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "mimicry",
        "fraud_reason": "Mimicry detected — no respondent was available during the interview. Surveyor is asking and answering questions by himself. Only one voice pattern detected throughout the recording. Account ID is '99-TEST' which itself is suspicious.",
        "quality_score": 0.5,
        "completeness_score": 2.0,
        "fraud_risk_score": 9.5,
        "technique_score": 1.0,
    },
    {
        "uid": 111792,
        "surveyor_name": "116491 - (Sundarlal Rangari)",
        "surveyor_id": "32-AVINASH BORKAR",
        "survey_date": "13-Mar-2026",
        "survey_time": "09:01:35",
        "time_difference_seconds": 1781,
        "actual_address": "2QXM+6P2, Kesalwada, Maharashtra 441804, India",
        "respondent_gender": "Male",
        "respondent_dob": "1988-10-16",
        "respondent_area": "Kesalwada wagh",
        "respondent_occupation": "Farmer",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\111792.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\n[Heavy background noise — walking sounds]\n[Footsteps audible throughout]\n[No clear voice detected for most of the recording]\nSurveyor (barely audible): ...gender... male...\n[More walking sounds]\n[No respondent voice detected]\n[Background traffic noise]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "fake_form",
        "fraud_reason": "Invalid — No clarity for actual respondent throughout the survey. Recording contains only background noise. Walking steps and traffic sounds are audible most of the time. Despite the long duration (1781s), no genuine interview took place.",
        "quality_score": 1.0,
        "completeness_score": 1.5,
        "fraud_risk_score": 9.0,
        "technique_score": 1.0,
    },
    {
        "uid": 108399,
        "surveyor_name": "115982 - (Maroti Gavhalkar)",
        "surveyor_id": "29-MAROTI GAVHALKAR",
        "survey_date": "05-Mar-2026",
        "survey_time": "13:13:31",
        "time_difference_seconds": 901,
        "actual_address": "G5FG+27X, Bodhadi Kh, Maharashtra 431810, India",
        "respondent_gender": "Male",
        "respondent_dob": "1977-07-01",
        "respondent_area": "Bodhadi Kh",
        "respondent_occupation": "Agricultural Worker",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\108399.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\nSurveyor: Gender? Male.\nSurveyor: Health problems? No.\nSurveyor: Treatment? Private hospitals.\n[Respondent present but not answering]\nSurveyor (filling in): Health schemes - don't know.\nSurveyor (filling in): Occupation - unemployed.\nSurveyor: Skill programs? Not aware.\nSurveyor (talking over respondent): Farming - yes, laborer.\n[Surveyor dominates entire conversation, respondent silent on major questions]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "force_survey",
        "fraud_reason": "Forceful survey — surveyor forcefully updated major health and skill questions. Although respondent appears present, they are not specifying any answers. Surveyor is self-promoting and filling in responses without genuine respondent input.",
        "quality_score": 2.5,
        "completeness_score": 4.0,
        "fraud_risk_score": 8.0,
        "technique_score": 2.0,
    },
    {
        "uid": 108827,
        "surveyor_name": "115982 - (Maroti Gavhalkar)",
        "surveyor_id": "29-MAROTI GAVHALKAR",
        "survey_date": "07-Mar-2026",
        "survey_time": "09:34:46",
        "time_difference_seconds": 756,
        "actual_address": "G5FF+8FG, Bodhadi Kh, Maharashtra 431810, India",
        "respondent_gender": "Male",
        "respondent_dob": "1977-01-01",
        "respondent_area": "Mahadev nagar",
        "respondent_occupation": "Agricultural Worker",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\108827.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\nSurveyor: Gender? Male.\nSurveyor: Any health issues? No.\n[Respondent barely speaks]\nSurveyor (filling answers): Goes to government hospital.\nSurveyor: Not enrolled in any scheme.\nSurveyor: Occupation - farm labor.\n[Surveyor continues self-promoting answers]\nSurveyor: Farming - yes, laborer.\n[Same surveyor as UID 108399 — similar pattern]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "force_survey",
        "fraud_reason": "Forceful survey — respondent is not answering questions. Surveyor is self-promoting and filling in responses. Same surveyor (Maroti Gavhalkar) shows consistent force-survey pattern across multiple interviews.",
        "quality_score": 2.5,
        "completeness_score": 4.0,
        "fraud_risk_score": 8.0,
        "technique_score": 2.0,
    },
    {
        "uid": 109261,
        "surveyor_name": "115982 - (Maroti Gavhalkar)",
        "surveyor_id": "29-MAROTI GAVHALKAR",
        "survey_date": "09-Mar-2026",
        "survey_time": "10:27:56",
        "time_difference_seconds": 1087,
        "actual_address": "2, Dahegaon, Maharashtra 431811, India",
        "respondent_gender": "Female",
        "respondent_dob": "1993-01-01",
        "respondent_area": "Dahegaon",
        "respondent_occupation": "Agricultural Worker",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\109261.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\nSurveyor: Gender? Female.\nSurveyor: Health issues? No.\n[Respondent silent]\nSurveyor (filling in): Private hospitals.\nSurveyor: Scheme enrollment? Don't know.\nSurveyor (answering himself): Process was easy, no difficulty.\nSurveyor: Occupation? Driver.\n[NOTE: Registered gender is Female but occupation recorded as Driver — inconsistency]\n[Surveyor filled major health and skill questions without respondent]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "force_survey",
        "fraud_reason": "Forceful survey — major health and skill questions filled without respondent's input. Same surveyor (Maroti Gavhalkar) again. Registered gender is Female but occupation listed as Driver — possible data inconsistency suggesting force-filling.",
        "quality_score": 2.0,
        "completeness_score": 3.5,
        "fraud_risk_score": 8.5,
        "technique_score": 1.5,
    },
    {
        "uid": 108417,
        "surveyor_name": "115982 - (Maroti Gavhalkar)",
        "surveyor_id": "29-MAROTI GAVHALKAR",
        "survey_date": "05-Mar-2026",
        "survey_time": "15:04:37",
        "time_difference_seconds": 786,
        "actual_address": "G5FG+HCR, TQ, Bodhadi Bk., Kinwat, Maharashtra 431810, India",
        "respondent_gender": "Female",
        "respondent_dob": "1995-01-01",
        "respondent_area": "Borsa munda",
        "respondent_occupation": "Agricultural Worker",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\108417.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\nSurveyor: Gender? Female.\nSurveyor: Health problems? No.\n[Respondent present but surveyor dominates]\nSurveyor (answers own questions): Government hospitals.\nSurveyor: Health schemes — don't know.\nSurveyor: Why not enrolled? None of the above.\nSurveyor: Occupation? Farm labor.\n[Surveyor dominated responses throughout]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "force_survey",
        "fraud_reason": "Forceful survey — surveyor dominated responses throughout. Same surveyor (Maroti Gavhalkar) showing consistent force-survey pattern. Respondent present but passive, surveyor fills in all answers.",
        "quality_score": 2.0,
        "completeness_score": 3.5,
        "fraud_risk_score": 8.0,
        "technique_score": 2.0,
    },
    {
        "uid": 111169,
        "surveyor_name": "115262 - (Rohini Salve)",
        "surveyor_id": "33-MOHD KHALID SHAIKH",
        "survey_date": "12-Mar-2026",
        "survey_time": "10:27:12",
        "time_difference_seconds": 734,
        "actual_address": "Ekta CHS, Govandi East, Mumbai, Maharashtra 400043, India",
        "respondent_gender": "Female",
        "respondent_dob": "1990-01-01",
        "respondent_area": "Govandi East",
        "respondent_occupation": "Businessmen with No employees",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\111169.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\n[Multiple voices detected]\nSurveyor: Gender?\nMale voice: Male.\n[NOTE: Registered gender is FEMALE but male voice is answering]\nSurveyor: Health issues?\nMale voice: Yes, asthma.\nSurveyor: Treatment?\nMale voice: Private hospitals.\nSurveyor: Occupation?\nMale voice: Small shop.\n[Female respondent expected but male is answering throughout]\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "force_survey",
        "fraud_reason": "Multiple respondents gave answers. Actual respondent registered as Female but Male voice captured answering all questions. This is gender mismatch fraud — wrong person is being interviewed or someone else is answering on behalf.",
        "quality_score": 3.0,
        "completeness_score": 5.0,
        "fraud_risk_score": 7.5,
        "technique_score": 3.0,
    },
    {
        "uid": 112210,
        "surveyor_name": "116522 - (Kiran Gayakwad)",
        "surveyor_id": "20-SIDDHARTH GAIKWAD",
        "survey_date": "13-Mar-2026",
        "survey_time": "10:42:02",
        "time_difference_seconds": 1713,
        "actual_address": "GVC2+CW Ranbothali, Maharashtra, India",
        "respondent_gender": "Male",
        "respondent_dob": "1980-12-19",
        "respondent_area": "Ranbothli",
        "respondent_occupation": "Electrician",
        "audio_url": r"d:\Zeex AI\MH Project 17-03-26\112210.wav",
        "transcript": "=== MOCK TRANSCRIPT ===\n[Two voices — male and female detected]\nSurveyor: Gender?\nMale voice: Male.\nSurveyor: Health issues?\nMale voice: No.\nSurveyor: Treatment?\nMale voice: Government hospitals.\nSurveyor: Occupation?\nMale voice: Electrician.\n[NOTE: Most answers given by male respondent — check if this is on behalf of a female respondent]\nSurveyor: Farming?\nMale voice: Yes, as farm worker.\n=== END ===",
        "fraud_detected": True,
        "fraud_type": "force_survey",
        "fraud_reason": "Most of the answers were given by male respondent on behalf of female respondent. Gender mismatch between registered and actual respondent voice. This indicates proxy answering — the actual respondent may not have been willing or available.",
        "quality_score": 3.5,
        "completeness_score": 6.0,
        "fraud_risk_score": 7.0,
        "technique_score": 3.5,
    },
]


def seed_database():
    """Insert sample records into the database."""
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        existing = db.query(AuditRecord).count()
        if existing > 0:
            print(f"Database already has {existing} records. Skipping seed.")
            print("To re-seed, delete zaudi.db first.")
            return

        for data in SAMPLE_RECORDS:
            record = AuditRecord(**data)
            db.add(record)

        db.commit()
        print(f"✅ Successfully seeded {len(SAMPLE_RECORDS)} records into the database!")
        print("\nSeeded UIDs:")
        for r in SAMPLE_RECORDS:
            fraud_emoji = {"fake_form": "👻", "mimicry": "🎭", "force_survey": "💪", "clean": "✅"}.get(r["fraud_type"], "❓")
            print(f"  {fraud_emoji} UID {r['uid']} — {r['fraud_type']} (score: {r['quality_score']})")

    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
