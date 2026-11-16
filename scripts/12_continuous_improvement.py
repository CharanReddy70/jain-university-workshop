"""
Module 12 (instructor-only demo, "Lab 9" in the original plan): continuous improvement.

  Part 1 (REAL call): ask AgentCore for an AI-generated system-prompt recommendation,
          based on CampusMate's own traces and the Builtin.Helpfulness evaluator.
  Part 2 (NARRATED):  how a Gateway A/B test would validate that recommendation on live
          traffic. Running it for real needs a second Runtime variant behind the Gateway,
          so we walk through the steps instead of spending money on it in class.

Both features were in PREVIEW on 2026-11-08. Run:  python scripts/12_continuous_improvement.py
"""
import json, sys, time
sys.path.insert(0, "projects")
import boto3, campusmate_agent

STUDENT_ID, REGION = "instructor", "us-east-1"
ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
dp = boto3.client("bedrock-agentcore", region_name=REGION)
rid = next(r["agentRuntimeId"] for r in ctl.list_agent_runtimes(maxResults=100)["agentRuntimes"]
           if r["agentRuntimeName"] == f"campusmate_{STUDENT_ID}")

print("PART 1 - recommendation from production traces (real API call)")
# Use a few recent *clean* sessions. Sessions full of prompt-injection attacks (Lab 11) can make the
# recommender's safety filters withhold the result, so we skip them.
logs = boto3.client("logs", region_name=REGION)
group = f"/aws/bedrock-agentcore/runtimes/{rid}-DEFAULT"
def records(filter_pattern, hours=24):
    out, tok = [], None
    while True:
        kw = dict(logGroupName=group, filterPattern=filter_pattern, startTime=int((time.time() - hours * 3600) * 1000))
        r = logs.filter_log_events(**({**kw, "nextToken": tok} if tok else kw)); tok = r.get("nextToken")
        out += [json.loads(e["message"]) for e in r["events"] if e["message"].startswith("{")]
        if not tok or len(out) > 400:
            return out
sessions = []
for rec in reversed(records('"invoke_agent"')):
    sid = rec.get("attributes", {}).get("session.id", "")
    if sid and sid not in sessions and not any(x in sid for x in ("lab11", "smoke", "capstone")):
        sessions.append(sid)
sessions = sessions[:4]
spans = [r for sid in sessions for r in records(f'"{sid}"') if r.get("attributes", {}).get("session.id")]  # API requires it
print(f"using {len(sessions)} clean sessions ({len(spans)} telemetry records):", [x[:18] for x in sessions])
rec = dp.start_recommendation(
    name=f"campusmate_prompt_{STUDENT_ID}_{int(time.time())}", type="SYSTEM_PROMPT_RECOMMENDATION",
    recommendationConfig={"systemPromptRecommendationConfig": {
        "systemPrompt": {"text": campusmate_agent.system_prompt("AIDD-DEMO-001")},
        "agentTraces": {"sessionSpans": spans},
        "evaluationConfig": {"evaluators": [{"evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness"}]}}},
    tags={"project": "campusmate-workshop", "student": STUDENT_ID})
rid = rec.get("recommendationId") or rec.get("recommendationArn")
print("started:", rid, "(this usually takes 5-15 minutes; narrate Part 2 meanwhile)")
for _ in range(80):
    r = dp.get_recommendation(recommendationId=rid)
    if r.get("status") not in ("PENDING", "IN_PROGRESS", "RUNNING", "CREATING"):
        break
    time.sleep(15)
print("status:", r.get("status"))
out = r.get("recommendationResult") or r.get("result") or {}
res = out.get("systemPromptRecommendationResult", out)
if res.get("errorCode"):
    print("Recommendation not available:", res.get("errorMessage"), "\n-> Narrate it instead: show notebook 10 scores and explain what a recommendation would change.")
else:
    print(json.dumps(res, indent=1, default=str)[:3000])

print("""
PART 2 - validate with a Gateway A/B test (narrated walkthrough)
 1. Put each agent version behind the Gateway as an HTTP target
    (targetConfiguration.http.agentcoreRuntime = {arn, qualifier}), or keep one Runtime and
    store the old/new system prompt in two versions of a *configuration bundle*.
 2. Create one online evaluation config per variant (same evaluators, e.g. Builtin.Helpfulness).
 3. bedrock-agentcore create-ab-test --gateway-arn <gw> --variants
      '[{"name":"C","weight":90,"variantConfiguration":{"target":{"name":"campusmate-v1"}}},
        {"name":"T1","weight":10,"variantConfiguration":{"target":{"name":"campusmate-v2"}}}]'
      --evaluation-config '{"perVariantOnlineEvaluationConfig":[...]}' --role-arn <role> --enable-on-create
 4. Send normal traffic to the control target; the Gateway splits it 90/10. Your code does not change.
 5. get-ab-test shows per-variant scores, confidence intervals and statistical significance.
 6. Stop the test (update-ab-test), route 100% to the winner, delete the test (delete-ab-test).
Campus analogy: two sections get different worksheet versions; you compare marks before
changing the worksheet for the whole batch.""")
