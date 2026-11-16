"""
submit_leave_request - the governed action for Lab 11 (Cedar policy at the Gateway).

Deliberately simple and stateless: it validates the input and returns a
confirmation. It does NOT enforce the 3-day limit itself. That is the point of
the lab: the limit is enforced by a Cedar policy at the AgentCore Gateway,
outside the agent and outside this function, so a tricked agent cannot bypass it.
"""
import hashlib
from datetime import date, datetime, timedelta


def lambda_handler(event, context):
    event = event or {}
    student_id = str(event.get("student_id", "")).strip().upper()
    reason = str(event.get("reason", "")).strip() or "Not given"
    try:
        days = int(event.get("days"))
    except (TypeError, ValueError):
        return {"submitted": False, "message": "days must be a whole number of days."}
    if days < 1:
        return {"submitted": False, "message": "days must be at least 1."}
    try:
        start = datetime.strptime(str(event.get("start_date")), "%Y-%m-%d").date()
    except ValueError:
        start = date.today() + timedelta(days=1)
    end = start + timedelta(days=days - 1)
    ref = "LV-" + hashlib.sha1(f"{student_id}{start}{days}{reason}".encode()).hexdigest()[:8].upper()
    return {
        "submitted": True,
        "reference": ref,
        "student_id": student_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days": days,
        "reason": reason,
        "status": "SUBMITTED",
        "note": "Fictional demo system. Nothing was stored.",
    }
