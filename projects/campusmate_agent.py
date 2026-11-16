"""
CampusMate - the finished reference agent (v8).

Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer
Science and Engineering, Jain (Deemed-to-be University), Bengaluru.

What is wired in:
  * Local tools       get_course_info, get_campus_policy   (read ../data/*.json)
  * Gateway tools     check_attendance_eligibility, submit_leave_request
                      (AWS Lambda behind AgentCore Gateway, guarded by a Cedar policy)
  * Memory            AgentCore Memory: short-term (this chat) + long-term
                      (facts/preferences and session summaries per student)
  * Runtime           BedrockAgentCoreApp entrypoint, so the same file runs
                      on your laptop AND on AgentCore Runtime.

Memory and Gateway tools switch on when these environment variables are set
(AgentCore Runtime sets them for you; Labs 6 and 7 show how):
  MEMORY_ID    -> memory on
  GATEWAY_URL  -> gateway tools on

Run it:
  python projects/campusmate_agent.py --chat                 # chat in the terminal
  python projects/campusmate_agent.py --chat --student AIDD-DEMO-003
  python projects/campusmate_agent.py                        # serve on :8080 like Runtime does
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path

from strands import Agent, tool
from strands.models import BedrockModel

logging.getLogger("strands").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
REGION = "us-east-1"
MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-2-lite-v1:0")   # Runtime may pass a cheaper model
MAX_TOKENS = 1200                       # headroom if the model "thinks" first; thinking counts as output
# Set by AgentCore. The AgentCore CLI (notebooks 05-12) names them after your memory / gateway;
# projects/deploy.sh uses the short names.
MEMORY_ID = os.environ.get("MEMORY_STUDENTMEMORY_ID") or os.environ.get("MEMORY_ID")
_cli_gateway = os.environ.get("AGENTCORE_GATEWAY_TOOLSGATEWAY_URL")
GATEWAY_URL = (_cli_gateway.rstrip("/") + "/mcp") if _cli_gateway else os.environ.get("GATEWAY_URL")
DEFAULT_STUDENT = "AIDD-DEMO-001"

# data/ sits next to this file inside the deployed zip, and one folder up in the repo
HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data" if (HERE / "data").is_dir() else HERE.parent / "data"


# ---------------------------------------------------------------------------
# Local tools (Lab 4). Plain Python functions + @tool. The docstring is what
# the model reads to decide WHEN to call the tool, so write it carefully.
# ---------------------------------------------------------------------------
def _load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@tool
def get_course_info(query: str) -> str:
    """Look up courses in the AIDD program by course code, title keyword or semester.

    Use this for questions about what a course covers, its credits, which
    semester it is in, or how it is assessed (internal marks, exams, labs).

    Args:
        query: A course code like "AIDD303", a keyword like "docker", or "semester 3".
    """
    q = query.strip().lower()
    courses = _load("courses.json")["courses"]
    if q.startswith("semester") or q.startswith("sem "):
        digits = "".join(ch for ch in q if ch.isdigit())
        hits = [c for c in courses if str(c["semester"]) == digits]
    else:
        words = [w for w in q.replace(",", " ").split() if len(w) > 1]
        hits = [
            c
            for c in courses
            if q == c["code"].lower()
            or any(w in (c["code"] + " " + c["title"] + " " + c["description"]).lower() for w in words)
        ]
    if not hits:
        return json.dumps({"found": False, "message": f"No course matches '{query}'.",
                           "available_codes": [c["code"] for c in courses]})
    return json.dumps({"found": True, "courses": hits[:5]})


@tool
def get_campus_policy(topic: str) -> str:
    """Return the official CampusMate rules for a campus topic.

    Topics: attendance, internal_assessments, semester_end_exams, fees, leave,
    re_evaluation, library, hackathons. Always use this tool instead of guessing
    a rule from memory.

    Args:
        topic: One of the topics above, or a close word like "exam", "fee", "OD".
    """
    policies = _load("campus_policies.json")["policies"]
    aliases = {
        "exam": "semester_end_exams", "exams": "semester_end_exams", "hall ticket": "semester_end_exams",
        "fee": "fees", "fees": "fees", "payment": "fees", "ia": "internal_assessments",
        "internal": "internal_assessments", "od": "hackathons", "hackathon": "hackathons",
        "book": "library", "books": "library", "revaluation": "re_evaluation",
        "re-evaluation": "re_evaluation", "absent": "attendance", "leave": "leave",
    }
    key = topic.strip().lower().replace(" ", "_")
    if key not in policies:
        key = aliases.get(topic.strip().lower(), key)
    if key not in policies:
        for k in policies:
            if k.split("_")[0] in topic.lower():
                key = k
                break
    if key not in policies:
        return json.dumps({"found": False, "message": f"No policy for '{topic}'.", "topics": list(policies)})
    return json.dumps({"found": True, "topic": key, **policies[key]})


LOCAL_TOOLS = [get_course_info, get_campus_policy]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
def system_prompt(student_id: str) -> str:
    return f"""You are CampusMate, a friendly assistant for students of the AI-Driven DevOps (AIDD)
program, School of Computer Science and Engineering. All data you can see is fictional demo data.

Today's date is {date.today().isoformat()}. You are chatting with student ID {student_id}.

How to work:
- For course questions call get_course_info. For rules call get_campus_policy. Never invent a rule.
- For attendance or exam eligibility call check_attendance_eligibility with the student's ID.
- To file leave call submit_leave_request. Leave above 3 days needs mentor approval, so do not file it.
- If a tool is not available, say what you would need instead of guessing.
- Keep answers short: 2-5 sentences or a short list. Use plain English and rupees (Rs.) for money.
"""


# ---------------------------------------------------------------------------
# Memory (Lab 6) and Gateway (Lab 7)
# ---------------------------------------------------------------------------
def memory_session_manager(session_id: str, actor_id: str, memory_id: str | None):
    if not memory_id:
        return None
    from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

    cfg = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config={
            # long-term facts and preferences about this student (semantic strategy)
            "/students/{actorId}/facts/": RetrievalConfig(top_k=5, relevance_score=0.3),
            # recaps of earlier chats (summary strategy)
            "/students/{actorId}/summaries/": RetrievalConfig(top_k=3, relevance_score=0.3),
            # the same, as named by `agentcore add memory --strategies SEMANTIC,SUMMARIZATION`
            "/users/{actorId}/facts": RetrievalConfig(top_k=5, relevance_score=0.3),
            "/summaries/{actorId}": RetrievalConfig(top_k=3, relevance_score=0.3),
        },
    )
    return AgentCoreMemorySessionManager(cfg, region_name=REGION)


def gateway_client(gateway_url: str | None):
    if not gateway_url:
        return None
    from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client
    from strands.tools.mcp import MCPClient

    # The Gateway uses AWS_IAM inbound auth: every request is SigV4-signed with
    # the caller's AWS credentials (the Runtime role when deployed, your IAM
    # user on your laptop).
    return MCPClient(
        lambda: aws_iam_streamablehttp_client(
            endpoint=gateway_url, aws_service="bedrock-agentcore", aws_region=REGION
        )
    )


def build_agent(session_id: str, actor_id: str = DEFAULT_STUDENT, memory_id: str | None = MEMORY_ID,
                gateway_url: str | None = GATEWAY_URL, model_id: str = MODEL_ID) -> Agent:
    tools: list = list(LOCAL_TOOLS)
    mcp = gateway_client(gateway_url)
    if mcp is not None:
        tools.append(mcp)  # Strands starts/stops the MCP connection for us
    model = BedrockModel(
        model_id=model_id,
        region_name=REGION,
        max_tokens=MAX_TOKENS,
    )
    return Agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt(actor_id),
        session_manager=memory_session_manager(session_id, actor_id, memory_id),
        callback_handler=None,  # no token streaming to stdout
        trace_attributes={"session.id": session_id, "student.id": actor_id},
    )


def run_turn(agent: Agent, prompt: str) -> dict:
    """Ask one question and return the answer plus which tools ran (for tests and the UI)."""
    start = len(agent.messages)
    usage_before = dict(agent.event_loop_metrics.accumulated_usage)
    result = agent(prompt)
    calls, results = {}, {}
    for msg in agent.messages[start:]:
        for block in msg.get("content", []):
            if "toolUse" in block:
                calls[block["toolUse"]["toolUseId"]] = block["toolUse"]
            if "toolResult" in block:
                results[block["toolResult"]["toolUseId"]] = block["toolResult"]
    tools_used = []
    for tid, use in calls.items():
        res = results.get(tid, {})
        text = " ".join(c.get("text", "") for c in res.get("content", []) if isinstance(c, dict))
        tools_used.append({"name": use["name"], "input": use.get("input"),
                           "status": res.get("status", "unknown"), "output": text[:600]})
    usage_after = agent.event_loop_metrics.accumulated_usage
    usage = {k: usage_after.get(k, 0) - usage_before.get(k, 0) for k in ("inputTokens", "outputTokens")}
    return {
        "result": str(result).strip(),
        "tools_used": tools_used,
        "usage": usage,
        "model": agent.model.config.get("model_id"),
    }


# ---------------------------------------------------------------------------
# AgentCore Runtime entrypoint (Lab 5). Runtime gives each session its own
# microVM, so caching agents per session in this dict keeps short-term context
# even without Memory, and a NEW session starts fresh.
# ---------------------------------------------------------------------------
from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402

app = BedrockAgentCoreApp()
_AGENTS: dict[tuple[str, str], Agent] = {}


@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    prompt = (payload or {}).get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "Send JSON like {\"prompt\": \"...\", \"student_id\": \"AIDD-DEMO-001\"}"}
    actor_id = payload.get("student_id") or DEFAULT_STUDENT
    session_id = (getattr(context, "session_id", None) or payload.get("session_id")
                  or f"local-{uuid.uuid4()}")
    key = (session_id, actor_id)
    if key not in _AGENTS:
        _AGENTS[key] = build_agent(session_id, actor_id)
    out = run_turn(_AGENTS[key], prompt)
    out.update({"session_id": session_id, "student_id": actor_id,
                "memory": bool(MEMORY_ID), "gateway": bool(GATEWAY_URL)})
    return out


def chat(student_id: str) -> None:
    session_id = f"cli-{student_id}-{uuid.uuid4()}"
    agent = build_agent(session_id, student_id)
    print(f"CampusMate ({MODEL_ID}) | student {student_id} | memory={bool(MEMORY_ID)} gateway={bool(GATEWAY_URL)}")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        out = run_turn(agent, q)
        for t in out["tools_used"]:
            print(f"   [tool] {t['name']}({json.dumps(t['input'])}) -> {t['status']}")
        print(f"CampusMate: {out['result']}\n")


if __name__ == "__main__":
    if "--chat" in sys.argv:
        sid = sys.argv[sys.argv.index("--student") + 1] if "--student" in sys.argv else DEFAULT_STUDENT
        chat(sid)
    else:
        app.run()  # http://localhost:8080/invocations and /ping, same contract as AgentCore Runtime
