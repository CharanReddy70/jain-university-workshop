"""
check_attendance_eligibility - an AWS Lambda tool exposed through AgentCore Gateway (Lab 7).

The Gateway calls this function with:
  event   = the tool arguments, e.g. {"student_id": "AIDD-DEMO-003", "course_code": "AIDD303"}
  context = metadata; context.client_context.custom["bedrockAgentCoreToolName"] is
            "<target>___check_attendance_eligibility"

Data is fictional demo data (students.json is bundled next to this file at deploy time).
"""
import json
import os

MIN_ATTENDANCE = 75  # placeholder rule, see data/campus_policies.json
_HERE = os.path.dirname(os.path.abspath(__file__))


def _students():
    for path in (os.path.join(_HERE, "students.json"), os.path.join(_HERE, "..", "..", "..", "data", "students.json")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return {s["student_id"]: s for s in json.load(f)["students"]}
    raise FileNotFoundError("students.json not found")


def lambda_handler(event, context):
    event = event or {}
    student_id = str(event.get("student_id", "")).strip().upper()
    course_code = str(event.get("course_code", "") or "").strip().upper()
    student = _students().get(student_id)
    if not student:
        return {"found": False, "message": f"No student with ID '{student_id}'. IDs look like AIDD-DEMO-001."}

    courses = student["attendance"]
    if course_code:
        if course_code not in courses:
            return {"found": False, "message": f"{student_id} is not enrolled in {course_code}.",
                    "enrolled_courses": list(courses)}
        courses = {course_code: courses[course_code]}

    report = []
    for code, pct in courses.items():
        report.append({
            "course_code": code,
            "attendance_percent": pct,
            "eligible_for_exam": pct >= MIN_ATTENDANCE,
            "shortfall_percent": max(0, MIN_ATTENDANCE - pct),
        })
    fees_ok = student["fee_status"] == "paid"
    all_ok = all(r["eligible_for_exam"] for r in report)
    return {
        "found": True,
        "student_id": student_id,
        "name": student["name"],
        "semester": student["semester"],
        "minimum_required_percent": MIN_ATTENDANCE,
        "courses": report,
        "fee_status": student["fee_status"],
        "hall_ticket_eligible": all_ok and fees_ok,
        "note": "Fictional demo data. 75% is a placeholder rule; check with the department office.",
    }
