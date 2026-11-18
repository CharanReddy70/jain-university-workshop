"""
Module 04 live demo: a Strands agent with two @tool functions over data/*.json.
Run: python scripts/04_strands_tools.py
"""
import json
from pathlib import Path
from strands import Agent, tool
from strands.models import BedrockModel

DATA = Path(__file__).resolve().parents[1] / "data"

@tool
def get_course_info(code: str) -> str:
    """Get title, credits, semester and assessment pattern for an AIDD course code like AIDD303."""
    courses = json.loads((DATA / "courses.json").read_text(encoding="utf-8"))["courses"]
    return json.dumps([c for c in courses if c["code"] == code.upper()] or "not found")

@tool
def get_campus_policy(topic: str) -> str:
    """Get campus rules for: attendance, fees, leave, library, hackathons, re_evaluation."""
    return json.dumps(json.loads((DATA / "campus_policies.json").read_text(encoding="utf-8"))["policies"].get(topic, "unknown topic"))

agent = Agent(model=BedrockModel(model_id="us.amazon.nova-2-lite-v1:0", region_name="us-east-1", max_tokens=1000),
              tools=[get_course_info, get_campus_policy],
              system_prompt="You are CampusMate. Use tools, never guess rules. Be brief.")
agent("How is AIDD303 assessed, and what attendance do I need to write its exam?")
print("\n\nTools called:", list(agent.event_loop_metrics.tool_metrics))
