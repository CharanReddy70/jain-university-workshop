"""
Module 01 live demo: LLMs hallucinate, are stateless, and temperature changes output.
Run: python scripts/01_genai_demos.py
"""
from strands import Agent
from strands.models import BedrockModel

MODEL_ID = "us.amazon.nova-2-lite-v1:0"                         # Amazon Nova 2 Lite
OLDER_MODEL_ID = MODEL_ID                                        # Nova accepts temperature

print("1) HALLUCINATION - there is no such rule, watch it make one up (or hedge):")
print(Agent(model=MODEL_ID, callback_handler=None)("Quote CampusMate Rule 42B from the Jain AIDD student handbook about canteen tokens, word for word."))

print("\n2) STATELESS - a new agent knows nothing about the old conversation:")
first = Agent(model=MODEL_ID, callback_handler=None)
print(first("Hi! My name is Priya and I'm in 3rd semester."))
print("new agent :", Agent(model=MODEL_ID, callback_handler=None)("What is my name and semester?"))
print("same agent:", first("What is my name and semester?"))

print("\n3) TEMPERATURE (Nova 2 Lite):")
for t in (0.0, 1.0):
    names = [str(Agent(model=BedrockModel(model_id=OLDER_MODEL_ID, temperature=t), callback_handler=None)(
        "Invent a 3-word name for a college tech fest. Reply with only the name.")).strip() for _ in range(2)]
    print(f"   temperature={t}:", names)
