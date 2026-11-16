"""
CampusMate shared configuration.

Every script, notebook and the deployed agent import settings from HERE, so
there is exactly one place to change the region, the model or your student ID.

Values come from (in order of priority):
  1. Real environment variables (this is how the deployed agent gets them)
  2. The .env file at the repo root (copy .env.example to .env)
  3. The defaults below

Model IDs were discovered in us-east-1 on 2026-11-08 with:
  aws bedrock list-inference-profiles --region us-east-1
Inference-profile prefixes are region-specific: "us." works for us-east-1 /
us-west-2, "eu." for European regions, "apac." for Asia Pacific (for example
ap-south-1, Mumbai). If you change AWS_REGION, change the model IDs too.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The deployed agent runs from a zip where config.py and data/ sit side by side.
# Locally, config.py is in projects/ and data/ is one level up.
REPO_ROOT = HERE.parent if (HERE.parent / "data").is_dir() and HERE.name == "projects" else HERE
DATA_DIR = HERE / "data" if (HERE / "data").is_dir() else REPO_ROOT / "data"

try:  # python-dotenv is optional inside the deployed agent
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=False)
except ImportError:  # pragma: no cover
    pass


def _clean_student_id(raw: str) -> str:
    """Lower-case letters and digits only, max 16 chars, so it is valid in every AWS name."""
    cleaned = re.sub(r"[^a-z0-9]", "", (raw or "").lower())[:16]
    return cleaned or "instructor"


# --------------------------------------------------------------------------
# Who you are and where you deploy
# --------------------------------------------------------------------------
STUDENT_ID = _clean_student_id(os.getenv("STUDENT_ID", "instructor"))
REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

# --------------------------------------------------------------------------
# Models (Amazon Bedrock inference profiles)
# --------------------------------------------------------------------------
# Amazon Nova 2 Lite for everything (no Anthropic model access needed).
# Override with DEFAULT_MODEL_ID / CHEAP_MODEL_ID / MODEL_ID in .env.
DEFAULT_MODEL_ID = os.getenv("DEFAULT_MODEL_ID", "us.amazon.nova-2-lite-v1:0")
CHEAP_MODEL_ID = os.getenv("CHEAP_MODEL_ID", "us.amazon.nova-2-lite-v1:0")
# MODEL_TIER=cheap picks CHEAP_MODEL_ID (the same model unless you change it).
MODEL_TIER = os.getenv("MODEL_TIER", "default").lower()
MODEL_ID = os.getenv("MODEL_ID") or (CHEAP_MODEL_ID if MODEL_TIER == "cheap" else DEFAULT_MODEL_ID)

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1200"))  # headroom for thinking; you pay only for tokens used

# Nova 2 Lite accepts `temperature` and `top_p`, so the temperature demos use it
# too (verified 2026-11-16). Claude 5.5 models would reject them.
SAMPLING_DEMO_MODEL_ID = os.getenv("SAMPLING_DEMO_MODEL_ID", "us.amazon.nova-2-lite-v1:0")


def supports_sampling_params(model_id: str) -> bool:
    """False for Claude 5.x models, which ignore/reject temperature and top_p."""
    return not re.search(r"claude-(sonnet|haiku|opus|fable)-5", model_id)

# On-demand prices in USD per 1,000 tokens (input, output) for the us. (regional)
# inference profiles in us-east-1, read from the AWS Price List API
# (service code AmazonBedrockFoundationModels) on 2026-11-08. Prices change:
# re-check https://aws.amazon.com/bedrock/pricing/ before quoting them.
PRICE_PER_1K = {
    "nova-2-lite": (0.00033, 0.00275),  # Amazon Nova 2 Lite: $0.33 / $2.75 per 1M tokens
    "sonnet": (0.0022, 0.011),     # Claude Sonnet 5.5: $2.20 / $11.00 per 1M tokens
    "haiku": (0.00011, 0.00055),   # Claude Haiku 5.5:  $0.11 / $0.55 per 1M tokens
}


def price_for(model_id: str) -> tuple[float, float]:
    if "nova-2-lite" in model_id:
        return PRICE_PER_1K["nova-2-lite"]
    return PRICE_PER_1K["haiku" if "haiku" in model_id else "sonnet"]


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = price_for(model_id)
    return input_tokens / 1000 * pin + output_tokens / 1000 * pout


def text_of(message: dict) -> str:
    """Join the text blocks of a Converse message.

    Claude 5.5 models may return a `reasoningContent` (thinking) block BEFORE
    the text, so never assume content[0] is text. Thinking tokens count as
    output tokens: if maxTokens is tiny the model can spend it all thinking and
    return no text (stopReason = "max_tokens").
    """
    return "".join(b.get("text", "") for b in message.get("content", []) if "text" in b)


# --------------------------------------------------------------------------
# Resource names. Every name contains STUDENT_ID so 40+ students can share
# one AWS account without colliding.
# --------------------------------------------------------------------------
SID = STUDENT_ID
NAMES = {
    "runtime": f"campusmate_{SID}",                  # [a-zA-Z][a-zA-Z0-9_]{0,47}
    "memory": f"campusmate_mem_{SID}",
    "gateway": f"campusmate-gw-{SID}",              # letters, digits, hyphens
    "attendance_lambda": f"campusmate-attendance-{SID}",
    "leave_lambda": f"campusmate-leave-{SID}",
    "attendance_target": "attendance",               # tool = attendance___check_attendance_eligibility
    "leave_target": "leave",                         # tool = leave___submit_leave_request
    "policy_engine": f"campusmate_pe_{SID}",
    "online_eval": f"campusmate_eval_{SID}",
    "runtime_role": f"campusmate-runtime-role-{SID}",
    "gateway_role": f"campusmate-gateway-role-{SID}",
    "lambda_role": f"campusmate-lambda-role-{SID}",
    "eval_role": f"campusmate-eval-role-{SID}",
}

TAGS = {"project": "campusmate-workshop", "student": SID}
PYTHON_RUNTIME = "PYTHON_3_12"  # AgentCore Runtime direct code deploy runtime


def bucket_name(account_id: str) -> str:
    return f"campusmate-{SID}-{account_id}-{REGION}"


# --------------------------------------------------------------------------
# Deployed resources registry (projects/.deployed-resources.json, git-ignored)
# Cleanup reads this file, so everything we create is written here.
# --------------------------------------------------------------------------
RESOURCES_FILE = Path(os.getenv("DEPLOYED_RESOURCES_FILE") or (HERE / ".deployed-resources.json"))  # override only for testing


def load_resources() -> dict:
    if RESOURCES_FILE.exists():
        data = json.loads(RESOURCES_FILE.read_text())
        if data.get("student_id") == SID:
            return data
    return {"student_id": SID, "region": REGION, "resources": {}}


def save_resource(key: str, value) -> None:
    data = load_resources()
    data["resources"][key] = value
    RESOURCES_FILE.write_text(json.dumps(data, indent=2))


def get_resource(key: str, default=None):
    """Env var wins (deployed agent), then the registry file (your laptop)."""
    env_key = key.upper()
    if os.getenv(env_key):
        return os.getenv(env_key)
    return load_resources()["resources"].get(key, default)


# Handy values the agent and the web app read
MEMORY_ID = get_resource("memory_id")
GATEWAY_URL = get_resource("gateway_url")
# Lets a student chat with a classmate's agent (notebook 08 exercise)
AGENT_ARN = os.getenv("CAMPUSMATE_AGENT_ARN") or get_resource("agent_runtime_arn")

if __name__ == "__main__":
    print(f"STUDENT_ID     : {STUDENT_ID}")
    print(f"REGION         : {REGION}")
    print(f"MODEL_ID       : {MODEL_ID}  (default={DEFAULT_MODEL_ID}, cheap={CHEAP_MODEL_ID})")
    print(f"MAX_TOKENS     : {MAX_TOKENS}")
    print(f"DATA_DIR       : {DATA_DIR}")
    for k, v in NAMES.items():
        print(f"  {k:18s} {v}")
    print(f"Deployed agent : {AGENT_ARN}")
