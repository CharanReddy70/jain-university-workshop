"""
CampusMate setup check - run this BEFORE Day 1. One command, clear PASS/FAIL lines.

Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer
Science and Engineering, Jain (Deemed-to-be University), Bengaluru.

    python scripts/check_setup.py
"""
import importlib
import importlib.metadata
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGION = "us-east-1"
MODELS = ["us.amazon.nova-2-lite-v1:0"]
failures = 0


def result(ok, what, fix=""):
    global failures
    print(f"[{'PASS' if ok else 'FAIL'}] {what}")
    if not ok:
        failures += 1
        print(f"       FIX: {fix}")
    return ok


# 1. Python version
v = sys.version_info
result(v >= (3, 10), f"Python {v.major}.{v.minor}.{v.micro} (need 3.10 or newer)",
       "Install Python 3.12 (macOS: brew install python@3.12, Windows: python.org installer), "
       "then recreate the venv: python3.12 -m venv .venv")
in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
result(in_venv, f"running inside a virtual environment ({sys.prefix})",
       "Activate it first. macOS: source .venv/bin/activate   Windows: .venv\\Scripts\\activate")

# 2. Packages
for mod, pip_name in [("boto3", "boto3"), ("strands", "strands-agents"), ("strands_tools", "strands-agents-tools"),
                      ("bedrock_agentcore", "bedrock-agentcore"), ("mcp_proxy_for_aws", "mcp-proxy-for-aws"),
                      ("flask", "flask"), ("dotenv", "python-dotenv")]:
    try:
        importlib.import_module(mod)
        result(True, f"import {mod} ({importlib.metadata.version(pip_name)})")
    except Exception as e:  # noqa: BLE001
        result(False, f"import {mod}: {e}", f"pip install -r requirements.txt   (package: {pip_name})")

# Command-line tools used to deploy the agent (notebook 05 onwards)
import shutil, subprocess


def version_of(cmd):
    path = shutil.which(cmd)
    if not path:
        return None
    try:
        return subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30).stdout.strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        return "installed"


node = version_of("node")
node_ok = bool(node) and node.lstrip("v").split(".")[0].isdigit() and int(node.lstrip("v").split(".")[0]) >= 20
result(node_ok, f"Node.js {node or 'not found'} (need 20 or newer)", "Install Node.js 20+ from https://nodejs.org (LTS), then reopen the terminal")
result(bool(version_of("agentcore")), f"AgentCore CLI {version_of('agentcore') or 'not found'}",
       "Run: npm install -g @aws/agentcore   then reopen the terminal")
result(bool(version_of("uv")), f"uv {version_of('uv') or 'not found'}",
       "macOS: brew install uv   Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")

try:
    from strands import Agent  # noqa: F401  (the real import - not `import strands_agents`)
    result(True, "from strands import Agent")
except Exception as e:  # noqa: BLE001
    result(False, f"from strands import Agent: {e}", "pip install -r requirements.txt")

# 4. AWS identity and region
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

try:
    ident = boto3.client("sts", region_name=REGION).get_caller_identity()
    result(True, f"AWS identity: {ident['Arn']} (account {ident['Account']})")
except NoCredentialsError:
    result(False, "AWS credentials not found", "Run `aws configure` and paste the access key your instructor gave you")
    sys.exit(1)
except ClientError as e:
    result(False, f"AWS credentials rejected: {e.response['Error']['Code']}",
           "Keys are wrong or expired. Run `aws configure` again with fresh keys")
    sys.exit(1)

cli_region = boto3.Session().region_name
result(cli_region == REGION, f"default AWS region is {cli_region} (need {REGION})",
       f"Run: aws configure set region {REGION}")

# 5. Bedrock model access (one tiny call, costs a fraction of a cent)
for model in MODELS:
    try:
        out = boto3.client("bedrock-runtime", region_name=REGION).converse(
            modelId=model, messages=[{"role": "user", "content": [{"text": "Say OK"}]}], inferenceConfig={"maxTokens": 300})
        text = "".join(b.get("text", "") for b in out["output"]["message"]["content"])
        result(True, f"Bedrock model access: {model} -> {text.strip()[:20]!r}")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        fix = {"AccessDeniedException": "Your IAM user needs bedrock:InvokeModel (see SETUP.md, Lab 1-4 permissions), "
                                        "or model access is not enabled for this model in this region.",
               "ValidationException": "Model ID not valid in this region. Use us-east-1.",
               "ThrottlingException": "Throttled. Wait a minute and retry."}.get(code, "See SETUP.md troubleshooting")
        result(False, f"Bedrock model {model}: {code} {e.response['Error']['Message'][:120]}", fix)

# 6. AgentCore reachable
try:
    boto3.client("bedrock-agentcore-control", region_name=REGION).list_agent_runtimes(maxResults=1)
    result(True, f"Amazon Bedrock AgentCore control plane reachable in {REGION}")
except ClientError as e:
    result(False, f"AgentCore: {e.response['Error']['Code']}",
           "Your IAM user needs bedrock-agentcore:ListAgentRuntimes (SETUP.md), and AgentCore must exist in your region")
except Exception as e:  # noqa: BLE001
    result(False, f"AgentCore: {e}", "Upgrade boto3: pip install -r requirements.txt")

print()
if failures:
    print(f"{failures} check(s) failed. Fix them using the FIX lines above, then run this again.")
    sys.exit(1)
print("All checks passed. You are ready for Day 1!")
