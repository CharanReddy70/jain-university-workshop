"""
Module 06 live demo: peek inside AgentCore Memory - what long-term records were
extracted for a student (facts/preferences and session summaries).
Run: python scripts/06_agentcore_memory.py AIDD-DEMO-001
"""
import sys
import boto3

STUDENT_ID, REGION = "instructor", "us-east-1"
student = sys.argv[1] if len(sys.argv) > 1 else "AIDD-DEMO-001"
ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
MEMORY_ID = next(m["id"] for m in ctl.list_memories(maxResults=100)["memories"]
                 if m["id"].startswith(f"campusmate_mem_{STUDENT_ID}-") and m["status"] == "ACTIVE")
mem = boto3.client("bedrock-agentcore", region_name=REGION)
for ns in (f"/students/{student}/facts/", f"/students/{student}/summaries/"):
    print(f"\n== {ns}")
    recs = mem.retrieve_memory_records(memoryId=MEMORY_ID, namespacePath=ns,
                                       searchCriteria={"searchQuery": "semester, interests, past questions", "topK": 5})
    for r in recs.get("memoryRecordSummaries", []):
        print(f" - ({r.get('score', 0):.2f}) {r['content']['text'][:160]}")
    if not recs.get("memoryRecordSummaries"):
        print(" (nothing yet - extraction runs in the background, give it ~1 minute)")
