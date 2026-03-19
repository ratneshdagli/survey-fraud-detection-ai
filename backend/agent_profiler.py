"""
Z-AUDIT — Agent Risk Profiler
Tracks cumulative fraud scores per agent across all their calls.
Enables cross-call pattern detection and duplicate answer matching.
"""
import json
from models import AuditRecord


def get_agent_risk_score(surveyor_id: str, db) -> dict:
    """
    Returns cumulative risk profile for an agent.
    Useful context to inject into the fraud detection prompt.
    """
    records = db.query(AuditRecord).filter(
        AuditRecord.surveyor_id == surveyor_id
    ).all()

    if not records:
        return {"agent_fraud_score": 0.0, "total_calls": 0, "fraud_calls": 0, "fraud_rate": 0.0}

    total = len(records)
    fraud_calls = sum(1 for r in records if r.fraud_detected)
    avg_fraud_risk = sum(r.fraud_risk_score or 0 for r in records) / total
    fraud_rate = fraud_calls / total

    # Composite agent risk: 60% fraud rate + 40% avg fraud risk score
    agent_score = min(10.0, (fraud_rate * 6.0) + (avg_fraud_risk * 0.4))

    return {
        "agent_fraud_score": round(agent_score, 1),
        "total_calls": total,
        "fraud_calls": fraud_calls,
        "fraud_rate": round(fraud_rate * 100, 1),
        "fraud_types": {
            "fake_form": sum(1 for r in records if r.fraud_type == "fake_form"),
            "mimicry": sum(1 for r in records if r.fraud_type == "mimicry"),
            "force_survey": sum(1 for r in records if r.fraud_type == "force_survey"),
        },
    }


def get_cross_call_context(uid: int, surveyor_id: str, db) -> str:
    """
    Checks if this agent has recent fraud flags — inject into prompt.
    """
    profile = get_agent_risk_score(surveyor_id, db)
    if profile["total_calls"] == 0:
        return "No prior call history for this agent."

    lines = [
        f"Agent {surveyor_id} history: {profile['total_calls']} total calls",
        f"Fraud rate: {profile['fraud_rate']}% ({profile['fraud_calls']} flagged calls)",
        f"Fraud types: Fake={profile['fraud_types']['fake_form']}, "
        f"Mimicry={profile['fraud_types']['mimicry']}, "
        f"Force={profile['fraud_types']['force_survey']}",
    ]

    if profile["fraud_rate"] > 50:
        lines.append("⚠️  HIGH RISK AGENT: More than half of this agent's calls were flagged.")
    elif profile["fraud_rate"] > 25:
        lines.append("⚠️  ELEVATED RISK: This agent has a notable fraud history.")

    return "\n".join(lines)


def check_duplicate_answers(uid: int, surveyor_id: str, answers: list, db) -> dict:
    """
    Compare key answers against other submissions by the same agent.
    Returns: {"has_duplicates": bool, "matching_uids": list, "duplicate_fields": list}
    """
    from preprocessing import UPLOAD_QUESTION_KEYWORDS

    # Get key answer values (skip upload questions)
    key_answers = [
        str(pair[0]).strip() for pair in answers
        if pair[0] and not any(kw in str(pair[1]).upper() for kw in UPLOAD_QUESTION_KEYWORDS)
    ][:10]  # Compare first 10 spoken answers

    # Load recent calls by same agent
    recent = db.query(AuditRecord).filter(
        AuditRecord.surveyor_id == surveyor_id,
        AuditRecord.uid != uid,
    ).order_by(AuditRecord.created_at.desc()).limit(20).all()

    matching_uids = []
    for record in recent:
        if not record.raw_json:
            continue
        try:
            raw = json.loads(record.raw_json)
            other_answers = [
                str(pair[0]).strip() for pair in raw.get("audioanswers", [])
                if pair[0] and not any(kw in str(pair[1]).upper() for kw in UPLOAD_QUESTION_KEYWORDS)
            ][:10]

            # Count matching answers
            matches = sum(1 for a, b in zip(key_answers, other_answers) if a == b)
            if matches >= 7:  # 70%+ match = suspicious
                matching_uids.append({"uid": record.uid, "match_count": matches})
        except Exception:
            continue

    return {
        "has_duplicates": len(matching_uids) > 0,
        "matching_uids": matching_uids,
        "note": (
            f"Found {len(matching_uids)} calls with 70%+ identical answers"
            if matching_uids
            else "No duplicate answer patterns found"
        ),
    }
