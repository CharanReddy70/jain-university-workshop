"""
Module 05 live demo: call the agent deployed on AgentCore Runtime. Same session ID keeps
context; a new session ID starts fresh (each session gets its own microVM).
Run: python scripts/05_agentcore_runtime.py
"""
import json, uuid
import boto3

STUDENT_ID, REGION = "instructor", "us-east-1"
ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
AGENT_ARN = next(r["agentRuntimeArn"] for r in ctl.list_agent_runtimes(maxResults=100)["agentRuntimes"]
                 if r["agentRuntimeName"] == f"campusmate_{STUDENT_ID}")
rt = boto3.client("bedrock-agentcore", region_name=REGION)

def ask(prompt, session):
    r = rt.invoke_agent_runtime(agentRuntimeArn=AGENT_ARN, runtimeSessionId=session,
                                payload=json.dumps({"prompt": prompt, "student_id": "AIDD-DEMO-001"}))
    return json.loads(r["response"].read())["result"]

a, b = f"demo-{uuid.uuid4()}", f"demo-{uuid.uuid4()}"   # 41 chars; Runtime needs >= 33
print("Session A:", ask("My favourite subject is Computer Networks. What is the fee late-payment rule?", a))
print("\nSession A again:", ask("What is my favourite subject?", a))
print("\nSession B (new):", ask("What is my favourite subject?", b))
