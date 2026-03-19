"""
Z-AUDIT — Preprocessing utilities for survey data.
Filters question types, counts answers, and estimates time budgets.
"""

UPLOAD_QUESTION_KEYWORDS = ["UPLOAD", "PHOTO", "IMAGE", "CAMERA", "SCAN", "DOCUMENT"]


def filter_spoken_questions(audioanswers: list) -> tuple:
    """
    Separates spoken questions from upload/photo tasks.
    Returns: (spoken_questions, upload_tasks)
    """
    spoken = []
    uploads = []
    for pair in audioanswers:
        question = str(pair[1]) if len(pair) > 1 else ""
        if any(kw in question.upper() for kw in UPLOAD_QUESTION_KEYWORDS):
            uploads.append(pair)
        else:
            spoken.append(pair)
    return spoken, uploads


def count_answered(spoken_questions: list) -> int:
    """Count questions that have a real answer (not None, not 'No answer')."""
    return sum(
        1 for pair in spoken_questions
        if pair[0] and str(pair[0]).strip().lower() not in ["no answer", "none", "null", ""]
    )


def format_answers_for_prompt(answers: list) -> str:
    """Format answers for the LLM prompt, marking UPLOAD questions."""
    if not answers:
        return "No answers recorded"

    spoken, uploads = filter_spoken_questions(answers)

    lines = []
    for i, a in enumerate(answers[:20]):
        if not isinstance(a, list) or len(a) < 2:
            continue
        q = str(a[1])[:200] if a[1] else "Unknown"
        ans = str(a[0])[:200] if a[0] else "No answer"
        is_upload = any(kw in q.upper() for kw in UPLOAD_QUESTION_KEYWORDS)
        tag = " [UPLOAD TASK — exclude from scoring]" if is_upload else ""
        lines.append(f"Q{i+1}{tag}: {q}\nA{i+1}: {ans}\n")

    summary = f"[{len(spoken)} spoken questions, {count_answered(spoken)} answered, {len(uploads)} upload tasks excluded]\n\n"
    return summary + "\n".join(lines) if lines else "No answers recorded"


def analyse_time_per_question(duration_seconds: int, spoken_questions: list) -> dict:
    """
    Given total duration and number of spoken questions,
    calculate average time per question and flag if unrealistic.
    """
    n = max(len(spoken_questions), 1)
    avg_time = duration_seconds / n

    flags = []
    if avg_time < 15:
        flags.append(f"Average {avg_time:.0f}s per question — too fast for trilingual questions")
    if duration_seconds < 400 and n >= 15:
        flags.append(f"Duration {duration_seconds}s for {n} questions — physically impossible to read all questions")

    return {
        "avg_seconds_per_question": round(avg_time, 1),
        "spoken_question_count": n,
        "time_flags": flags,
        "verdict": "suspicious" if flags else "acceptable",
    }
