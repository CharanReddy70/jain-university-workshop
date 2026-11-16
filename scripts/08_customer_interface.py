"""
Module 08 live demo: what the browser does, without a browser. Uses Flask's test
client to POST to /api/chat, which calls the deployed agent with a student as actor ID.
Run: python scripts/08_customer_interface.py      (the real app: python projects/web/app.py)
"""
import sys
sys.path.insert(0, "projects/web")
import app as webapp

webapp.STUDENT_ID, webapp.RUNTIME_NAME = "instructor", "campusmate_instructor"   # whose agent to talk to
client = webapp.app.test_client()
for student, question in [("AIDD-DEMO-005", "Can I get my hall ticket?"),
                          ("AIDD-DEMO-008", "Can I join an external hackathon with OD attendance?")]:
    data = client.post("/api/chat", json={"message": question, "student_id": student}).get_json()
    print(f"\n[{student}] {question}\n -> {data.get('result') or data.get('error')}")
    print("    tools:", [t["name"] for t in data.get("tools_used", [])], "| session:", data.get("session_id"))
