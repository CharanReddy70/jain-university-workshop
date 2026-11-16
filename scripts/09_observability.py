"""
Module 09 live demo: read the agent's OpenTelemetry spans from CloudWatch Logs and show
which tools ran, how long each step took, and how many tokens were used.
Run: python scripts/09_observability.py
"""
import time
import boto3

STUDENT_ID, REGION = "instructor", "us-east-1"
ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
rid = next(r["agentRuntimeId"] for r in ctl.list_agent_runtimes(maxResults=100)["agentRuntimes"]
           if r["agentRuntimeName"] == f"campusmate_{STUDENT_ID}")
LOG_GROUP = f"/aws/bedrock-agentcore/runtimes/{rid}-DEFAULT"
QUERY = """fields @timestamp, name, durationNano / 1000000 as ms, `attributes.session.id` as session,
       `attributes.gen_ai.usage.input_tokens` as tin, `attributes.gen_ai.usage.output_tokens` as tout,
       `attributes.gen_ai.tool.status` as status
| filter @logStream = 'spans' and (name like /invoke_agent|execute_tool/ or name = 'chat')
| sort @timestamp desc | limit 25"""
logs = boto3.client("logs", region_name=REGION)
q = logs.start_query(logGroupName=LOG_GROUP, startTime=int(time.time()) - 3 * 3600, endTime=int(time.time()), queryString=QUERY)["queryId"]
while (r := logs.get_query_results(queryId=q))["status"] in ("Running", "Scheduled"):
    time.sleep(1)
for row in r["results"]:
    f = {c["field"]: c["value"] for c in row}
    print(f"{f.get('@timestamp','')[11:19]} {f.get('session','')[:14]:14s} {f.get('name','')[:28]:28s} "
          f"{float(f.get('ms', 0)):7.0f} ms  tokens in/out={f.get('tin','-')}/{f.get('tout','-')} {f.get('status','')}")
print(f"\nOpen the traces: CloudWatch console -> GenAI Observability -> Bedrock AgentCore -> campusmate_{STUDENT_ID}")
