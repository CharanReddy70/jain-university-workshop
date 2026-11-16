"""
Module 03 live demo: your first Strands agent, one idea at a time.
Run: python scripts/03_first_agent.py
"""
from strands import Agent, tool

# 1) An agent in 3 lines
agent = Agent(model="us.amazon.nova-2-lite-v1:0")
agent("Hi! In two sentences, what can an AI assistant do for a college student?")

# 2) A personality + a conversation it remembers
campusmate = Agent(model="us.amazon.nova-2-lite-v1:0",
                   system_prompt="You are CampusMate, a friendly assistant for AIDD students. Be brief.")
campusmate("\nHi, I'm Kiran and I love cloud computing.")
campusmate("\nWhat's my name, and which topic do I like?")

# 3) Its first tool
@tool
def get_credits(course_code: str) -> int:
    """Return the number of credits for an AIDD course code such as AIDD303."""
    return {"AIDD202": 2, "AIDD303": 4}.get(course_code.upper(), 0)

helper = Agent(model="us.amazon.nova-2-lite-v1:0", tools=[get_credits])
result = helper("\nHow many credits are AIDD303 and AIDD202 together?")
print("\n\nTools used:", list(helper.event_loop_metrics.tool_metrics), "| tokens:", result.metrics.accumulated_usage["totalTokens"])
