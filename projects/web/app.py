"""
CampusMate chat portal (Lab 8) - a small Flask app that talks to YOUR agent
running on Amazon Bedrock AgentCore Runtime.

Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer
Science and Engineering, Jain (Deemed-to-be University), Bengaluru.

There is no login. You pick a fictional student from the dropdown; that student
ID becomes the AgentCore Memory "actor ID", so CampusMate remembers each
student separately. Each browser gets its own Runtime session ID (at least 33
characters, which Runtime requires).

Before you run it: put YOUR student ID in STUDENT_ID below (the same one you used in the notebooks).

Run:      python projects/web/app.py        then open http://localhost:5050
Options:  PORT=8000 python projects/web/app.py
          CAMPUSMATE_AGENT_ARN=<a classmate's agent ARN> python projects/web/app.py
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from flask import Flask, jsonify, render_template, request, session

# ---------------------------------------------------------------------------
# Settings: change STUDENT_ID to your own
# ---------------------------------------------------------------------------
STUDENT_ID = "student01"                 # e.g. priya07 (same as in your notebooks)
REGION = "us-east-1"
RUNTIME_NAME = f"campusmate{STUDENT_ID}_default_agent"   # the agent you deployed in notebook 05 (agentcore deploy)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

BRANDING = ("Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science "
            "and Engineering, Jain (Deemed-to-be University), Bengaluru")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)

_client = None


_found_arn = None


def agent_arn() -> str | None:
    """CAMPUSMATE_AGENT_ARN wins (to chat with a classmate's agent); otherwise find YOUR agent by its name."""
    global _found_arn
    if os.getenv("CAMPUSMATE_AGENT_ARN"):
        return os.getenv("CAMPUSMATE_AGENT_ARN")
    if _found_arn is None:
        ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
        token = None
        while True:
            page = ctl.list_agent_runtimes(**({"nextToken": token} if token else {}))
            for r in page["agentRuntimes"]:
                if r["agentRuntimeName"] == RUNTIME_NAME:
                    _found_arn = r["agentRuntimeArn"]
                    return _found_arn
            token = page.get("nextToken")
            if not token:
                return None
    return _found_arn


def runtime_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agentcore", region_name=REGION,
                               config=BotoConfig(read_timeout=120, retries={"max_attempts": 2}))
    return _client


def students() -> list[dict]:
    data = json.loads((DATA_DIR / "students.json").read_text(encoding="utf-8"))
    return [{"id": s["student_id"], "name": s["name"], "semester": s["semester"]} for s in data["students"]]


def session_id_for(student_id: str) -> str:
    """One Runtime session per (browser, student). Runtime needs >= 33 characters."""
    sessions = session.setdefault("runtime_sessions", {})
    if student_id not in sessions:
        sessions[student_id] = f"web-{uuid.uuid4()}-{uuid.uuid4().hex[:8]}"  # 49 chars
        session.modified = True
    return sessions[student_id]


@app.get("/")
def index():
    return render_template("index.html", branding=BRANDING, students=students(),
                           agent_arn=agent_arn() or "", student_suffix=STUDENT_ID)


@app.get("/api/health")
def health():
    arn = agent_arn()
    return jsonify({"agent_arn": arn, "configured": bool(arn), "region": REGION})


@app.post("/api/new-session")
def new_session():
    sid = (request.get_json(silent=True) or {}).get("student_id", "")
    session.get("runtime_sessions", {}).pop(sid, None)
    session.modified = True
    return jsonify({"ok": True, "session_id": session_id_for(sid) if sid else None})


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    student_id = body.get("student_id") or "AIDD-DEMO-001"
    if not message:
        return jsonify({"error": "Type a message first."}), 400
    arn = agent_arn()
    if not arn:
        return jsonify({"error": f"No agent called {RUNTIME_NAME} found. Check STUDENT_ID at the top of "
                                 "projects/web/app.py and that you finished notebook 05."}), 503
    sid = session_id_for(student_id)
    try:
        resp = runtime_client().invoke_agent_runtime(
            agentRuntimeArn=arn, runtimeSessionId=sid, qualifier="DEFAULT",
            payload=json.dumps({"prompt": message, "student_id": student_id}).encode())
        raw = resp["response"].read().decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"result": raw}
        if isinstance(data, str):
            data = {"result": data}
        data["session_id"] = sid
        return jsonify(data)
    except NoCredentialsError:
        return jsonify({"error": "No AWS credentials. Run `aws configure`, then restart the app."}), 500
    except EndpointConnectionError as e:
        return jsonify({"error": f"Cannot reach AgentCore ({e}). Check your internet and AWS_REGION."}), 502
    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = e.response["Error"]["Message"]
        hint = {
            "ResourceNotFoundException": "The agent ARN is wrong or the agent was deleted.",
            "AccessDeniedException": "Your IAM user needs bedrock-agentcore:InvokeAgentRuntime on this agent.",
            "ThrottlingException": "Too many requests. Wait a few seconds and try again.",
            "ValidationException": "Check the agent ARN and that the session ID is at least 33 characters.",
        }.get(code, "See the terminal running app.py for details.")
        app.logger.error("invoke failed: %s %s", code, msg)
        return jsonify({"error": f"Agent unreachable ({code}): {msg[:200]}. {hint}"}), 502


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))  # 5000 is taken by AirPlay on many Macs
    print(f"CampusMate portal on http://localhost:{port}  (agent: {agent_arn() or 'NOT CONFIGURED'})")
    app.run(host="127.0.0.1", port=port, debug=False)
