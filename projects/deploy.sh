#!/usr/bin/env bash
# =============================================================================
# CampusMate - deploy the whole reference system for ONE student, idempotently.
#
# Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer
# Science and Engineering, Jain (Deemed-to-be University), Bengaluru.
#
# Usage (from the repo root, with your venv active):
#   bash projects/deploy.sh            # everything
#   bash projects/deploy.sh runtime    # one stage only
#
# Stages, in order:
#   observability  check/enable CloudWatch Transaction Search (account-level, one time)
#   roles          IAM roles for Runtime, Gateway, Lambda and Evaluations (least privilege)
#   lambdas        check_attendance_eligibility + submit_leave_request
#   memory         AgentCore Memory with semantic + summary strategies
#   gateway        AgentCore Gateway (AWS_IAM inbound auth) + 2 Lambda targets
#   policy         Policy engine + Cedar policies, attached to the Gateway in ENFORCE mode
#   runtime        package projects/ for ARM64 and create/update the AgentCore Runtime
#   eval           online evaluation config with built-in evaluators
#
# Safe to re-run: every step looks for an existing resource by name first.
# Every resource name contains STUDENT_ID (from .env) and every ARN/ID is
# written to projects/.deployed-resources.json for exact cleanup.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "$ROOT/.venv/bin/python" ]]; then PY="$ROOT/.venv/bin/python";
elif [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then PY="$ROOT/.venv/Scripts/python.exe";
else PY="${PYTHON:-python3}"; fi

STAGES="${*:-all}"
echo "== CampusMate deploy | python: $PY | stages: $STAGES"

cd "$ROOT"
exec "$PY" -u - "$STAGES" <<'PYEOF'
import io, json, os, sys, time, zipfile, hashlib, subprocess, shutil
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "projects"))
import config  # noqa: E402
import boto3   # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

STAGES = sys.argv[1].split()
ALL = ["observability", "roles", "lambdas", "memory", "gateway", "policy", "runtime", "eval"]
if STAGES == ["all"]:
    STAGES = ALL
bad = [s for s in STAGES if s not in ALL]
if bad:
    sys.exit(f"Unknown stage(s): {bad}. Choose from: {ALL}")

R, N, SID = config.REGION, config.NAMES, config.SID
session = boto3.Session(region_name=R)
sts = session.client("sts")
try:
    ACCOUNT = sts.get_caller_identity()["Account"]
except Exception as e:  # noqa: BLE001
    sys.exit(f"AWS credentials problem: {e}\nFix: run `aws configure` (or `aws sso login`) and try again.")
iam = session.client("iam")
ctl = session.client("bedrock-agentcore-control")
lam = session.client("lambda")
s3 = session.client("s3")
logs = session.client("logs")
TAGS = config.TAGS
TAG_LIST = [{"Key": k, "Value": v} for k, v in TAGS.items()]
config.save_resource("account_id", ACCOUNT)
config.save_resource("region", R)
print(f"   account {ACCOUNT} | region {R} | student {SID} | model {config.MODEL_ID}")


def step(msg):
    print(f"\n-- {msg}")


def wait(fn, ok, bad=("FAILED", "CREATE_FAILED", "UPDATE_FAILED"), what="resource", timeout=900, every=10):
    t0 = time.time()
    while True:
        status = fn()
        if status in ok:
            return status
        if status in bad:
            raise RuntimeError(f"{what} ended in status {status}")
        if time.time() - t0 > timeout:
            raise TimeoutError(f"{what} still {status} after {timeout}s")
        print(f"   ... {what} is {status}")
        time.sleep(every)


def find(list_fn, key, name, name_field="name", **kw):
    """Generic find-by-name across paginated AgentCore list calls."""
    token = None
    while True:
        args = dict(kw)
        if token:
            args["nextToken"] = token
        resp = list_fn(**args)
        for item in resp.get(key, []):
            if item.get(name_field) == name:
                return item
        token = resp.get("nextToken")
        if not token:
            return None


# ----------------------------------------------------------------------------
# observability: Transaction Search is an ACCOUNT-level CloudWatch setting.
# ----------------------------------------------------------------------------
def stage_observability():
    step("Observability: CloudWatch Transaction Search")
    xray = session.client("xray")
    dest = xray.get_trace_segment_destination()
    if dest.get("Destination") == "CloudWatchLogs":
        print(f"   already enabled ({dest.get('Status')}) - nothing to do")
        return
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "TransactionSearchXRayAccess", "Effect": "Allow",
            "Principal": {"Service": "xray.amazonaws.com"}, "Action": "logs:PutLogEvents",
            "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:aws/spans:*",
                         f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/application-signals/data:*"],
            "Condition": {"ArnLike": {"aws:SourceArn": f"arn:aws:xray:{R}:{ACCOUNT}:*"},
                          "StringEquals": {"aws:SourceAccount": ACCOUNT}},
        }],
    }
    logs.put_resource_policy(policyName="TransactionSearchXRayAccess", policyDocument=json.dumps(policy))
    xray.update_trace_segment_destination(Destination="CloudWatchLogs")
    print("   enabled. Spans can take ~10 minutes to appear the very first time.")


# ----------------------------------------------------------------------------
# roles
# ----------------------------------------------------------------------------
def trust(service, agentcore=False):
    stmt = {"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}
    if agentcore:  # confused-deputy protection
        stmt["Condition"] = {"StringEquals": {"aws:SourceAccount": ACCOUNT},
                             "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{R}:{ACCOUNT}:*"}}
    return {"Version": "2012-10-17", "Statement": [stmt]}


def ensure_role(name, trust_doc, policy_doc, desc):
    try:
        arn = iam.get_role(RoleName=name)["Role"]["Arn"]
        iam.update_assume_role_policy(RoleName=name, PolicyDocument=json.dumps(trust_doc))
        print(f"   role {name} exists")
        created = False
    except iam.exceptions.NoSuchEntityException:
        arn = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust_doc),
                              Description=desc, Tags=TAG_LIST)["Role"]["Arn"]
        print(f"   role {name} created")
        created = True
    iam.put_role_policy(RoleName=name, PolicyName="campusmate-permissions", PolicyDocument=json.dumps(policy_doc))
    return arn, created


def stage_roles():
    step("IAM roles (least privilege, scoped to this student's resources)")
    rt, gw, lm = N["runtime"], N["gateway"], N
    bedrock_models = {
        "Sid": "InvokeBedrockModels", "Effect": "Allow",
        "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        "Resource": ["arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                     "arn:aws:bedrock:*::foundation-model/amazon.nova-*",
                     f"arn:aws:bedrock:{R}:{ACCOUNT}:inference-profile/*amazon.nova-*",
                     f"arn:aws:bedrock:{R}:{ACCOUNT}:inference-profile/*anthropic.claude-*"],
    }
    runtime_policy = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["logs:DescribeLogStreams", "logs:CreateLogGroup"],
         "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/bedrock-agentcore/runtimes/*"]},
        {"Effect": "Allow", "Action": ["logs:PutResourcePolicy"],
         "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/bedrock-agentcore/runtimes/{rt}-*"]},
        {"Effect": "Allow", "Action": ["logs:DescribeLogGroups"],
         "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:*"]},
        {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*",
                      f"arn:aws:logs:{R}:{ACCOUNT}:log-group:aws/spans:*"]},
        {"Effect": "Allow", "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords",
                                       "xray:GetSamplingRules", "xray:GetSamplingTargets"], "Resource": "*"},
        {"Effect": "Allow", "Action": "cloudwatch:PutMetricData", "Resource": "*",
         "Condition": {"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}}},
        bedrock_models,
        {"Sid": "ReadOwnCodePackage", "Effect": "Allow", "Action": ["s3:GetObject"],
         "Resource": [f"arn:aws:s3:::{config.bucket_name(ACCOUNT)}/*"]},
        {"Sid": "UseOwnMemory", "Effect": "Allow",
         "Action": ["bedrock-agentcore:CreateEvent", "bedrock-agentcore:GetEvent", "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:ListSessions", "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords", "bedrock-agentcore:GetMemoryRecord",
                    "bedrock-agentcore:GetMemory"],
         "Resource": [f"arn:aws:bedrock-agentcore:{R}:{ACCOUNT}:memory/{N['memory']}-*"]},
        {"Sid": "CallOwnGateway", "Effect": "Allow", "Action": ["bedrock-agentcore:InvokeGateway"],
         "Resource": [f"arn:aws:bedrock-agentcore:{R}:{ACCOUNT}:gateway/{gw}-*"]},
    ]}
    arn, _ = ensure_role(N["runtime_role"], trust("bedrock-agentcore.amazonaws.com", True), runtime_policy,
                         "CampusMate AgentCore Runtime execution role")
    config.save_resource("runtime_role_arn", arn)

    lambda_policy = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/lambda/campusmate-*-{SID}:*",
                      f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/lambda/campusmate-*-{SID}"]}]}
    arn, created = ensure_role(N["lambda_role"], trust("lambda.amazonaws.com"), lambda_policy,
                               "CampusMate Lambda tools execution role")
    config.save_resource("lambda_role_arn", arn)

    gateway_policy = {"Version": "2012-10-17", "Statement": [
        {"Sid": "InvokeOwnToolLambdas", "Effect": "Allow", "Action": ["lambda:InvokeFunction"],
         "Resource": [f"arn:aws:lambda:{R}:{ACCOUNT}:function:{lm['attendance_lambda']}",
                      f"arn:aws:lambda:{R}:{ACCOUNT}:function:{lm['leave_lambda']}"]},
        {"Sid": "EvaluateOwnPolicyEngine", "Effect": "Allow",
         "Action": ["bedrock-agentcore:AuthorizeAction", "bedrock-agentcore:PartiallyAuthorizeActions",
                    "bedrock-agentcore:GetPolicyEngine"],
         "Resource": [f"arn:aws:bedrock-agentcore:{R}:{ACCOUNT}:policy-engine/{N['policy_engine']}-*",
                      f"arn:aws:bedrock-agentcore:{R}:{ACCOUNT}:gateway/{gw}-*"]},
    ]}
    arn, _ = ensure_role(N["gateway_role"], trust("bedrock-agentcore.amazonaws.com", True), gateway_policy,
                         "CampusMate AgentCore Gateway service role")
    config.save_resource("gateway_role_arn", arn)

    eval_policy = {"Version": "2012-10-17", "Statement": [
        {"Sid": "ReadAgentTelemetry", "Effect": "Allow",
         "Action": ["logs:DescribeLogGroups", "logs:StartQuery", "logs:GetQueryResults", "logs:FilterLogEvents",
                    "logs:GetLogEvents", "logs:DescribeLogStreams"],
         "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/bedrock-agentcore/*",
                      f"arn:aws:logs:{R}:{ACCOUNT}:log-group:aws/spans",
                      f"arn:aws:logs:{R}:{ACCOUNT}:log-group:aws/spans:*",
                      f"arn:aws:logs:{R}:{ACCOUNT}:log-group:*"]},
        {"Sid": "WriteEvaluationResults", "Effect": "Allow",
         "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": [f"arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/bedrock-agentcore/evaluations/*"]},
        {"Effect": "Allow", "Action": "cloudwatch:PutMetricData", "Resource": "*",
         "Condition": {"StringLike": {"cloudwatch:namespace": "Bedrock-AgentCore*"}}},
        {"Sid": "JudgeModels", "Effect": "Allow",
         "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
         "Resource": ["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:*:{ACCOUNT}:inference-profile/*"]},
    ]}
    arn, _ = ensure_role(N["eval_role"], trust("bedrock-agentcore.amazonaws.com", True), eval_policy,
                         "CampusMate AgentCore Evaluations execution role")
    config.save_resource("eval_role_arn", arn)
    if created:
        print("   waiting 10s for new IAM roles to propagate")
        time.sleep(10)


# ----------------------------------------------------------------------------
# lambdas
# ----------------------------------------------------------------------------
def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for arcname, path in files:
            info = zipfile.ZipInfo(arcname, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, Path(path).read_bytes())
    return buf.getvalue()


def ensure_lambda(name, folder, extra_files=()):
    role = config.get_resource("lambda_role_arn") or iam.get_role(RoleName=N["lambda_role"])["Role"]["Arn"]
    code = zip_bytes([("handler.py", folder / "handler.py"), *extra_files])
    try:
        lam.get_function(FunctionName=name)
        lam.update_function_code(FunctionName=name, ZipFile=code)
        lam.get_waiter("function_updated_v2").wait(FunctionName=name)
        print(f"   lambda {name} updated")
    except lam.exceptions.ResourceNotFoundException:
        for attempt in range(6):  # new roles can take a few seconds to be assumable
            try:
                lam.create_function(FunctionName=name, Runtime="python3.12", Role=role, Handler="handler.lambda_handler",
                                    Code={"ZipFile": code}, Architectures=["arm64"], Timeout=15, MemorySize=256,
                                    Description="CampusMate workshop tool (fictional data)", Tags=TAGS)
                break
            except lam.exceptions.InvalidParameterValueException as e:
                if "role" not in str(e).lower() or attempt == 5:
                    raise
                time.sleep(5)
        lam.get_waiter("function_active_v2").wait(FunctionName=name)
        print(f"   lambda {name} created")
    arn = lam.get_function(FunctionName=name)["Configuration"]["FunctionArn"]
    return arn


def stage_lambdas():
    step("Lambda tools")
    base = ROOT / "projects" / "lambda"
    a = ensure_lambda(N["attendance_lambda"], base / "check_attendance_eligibility",
                      [("students.json", ROOT / "data" / "students.json")])
    config.save_resource("attendance_lambda_arn", a)
    b = ensure_lambda(N["leave_lambda"], base / "submit_leave_request")
    config.save_resource("leave_lambda_arn", b)


# ----------------------------------------------------------------------------
# memory
# ----------------------------------------------------------------------------
MEMORY_STRATEGIES = [
    {"semanticMemoryStrategy": {
        "name": "StudentFacts",
        "description": "Facts and preferences: branch, semester, interests",
        "namespaceTemplates": ["/students/{actorId}/facts/"]}},
    {"summaryMemoryStrategy": {
        "name": "SessionRecaps",
        "description": "Short recap of each chat session",
        "namespaceTemplates": ["/students/{actorId}/summaries/{sessionId}/"]}},
]


def stage_memory():
    step("AgentCore Memory")
    existing = None
    token = None
    while True:
        resp = ctl.list_memories(**({"nextToken": token} if token else {}))
        for mem in resp.get("memories", []):
            if mem["id"].startswith(N["memory"] + "-") and mem.get("status") != "DELETING":
                existing = mem
        token = resp.get("nextToken")
        if not token:
            break
    def deleting_same_name():
        return [m["id"] for m in ctl.list_memories().get("memories", [])
                if m["id"].startswith(N["memory"] + "-") and m.get("status") == "DELETING"]
    if not existing and deleting_same_name():
        # Right after cleanup the old memory may still be DELETING, and its name stays reserved until it is gone.
        print("   an earlier memory with this name is still being deleted (can take 10-30 min); waiting...")
        wait(lambda: "DELETING" if deleting_same_name() else "GONE", ok=("GONE",), bad=(), what="old memory deletion",
             timeout=2700, every=30)
    if existing:
        mid = existing["id"]
        print(f"   memory {mid} exists")
    else:
        mid = ctl.create_memory(name=N["memory"], description="CampusMate student memory (workshop)",
                                eventExpiryDuration=30, memoryStrategies=MEMORY_STRATEGIES, tags=TAGS)["memory"]["id"]
        print(f"   memory {mid} created (takes 1-3 minutes to become ACTIVE)")
    wait(lambda: ctl.get_memory(memoryId=mid)["memory"]["status"], ok=("ACTIVE",), what="memory")
    mem = ctl.get_memory(memoryId=mid)["memory"]
    config.save_resource("memory_id", mid)
    config.save_resource("memory_arn", mem["arn"])


# ----------------------------------------------------------------------------
# gateway
# ----------------------------------------------------------------------------
def load_schema(folder):
    return json.loads((ROOT / "projects" / "lambda" / folder / "tool_schema.json").read_text())


def ensure_target(gid, name, lambda_arn, schema):
    cfg = {"mcp": {"lambda": {"lambdaArn": lambda_arn, "toolSchema": {"inlinePayload": schema}}}}
    creds = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
    t = find(ctl.list_gateway_targets, "items", name, gatewayIdentifier=gid)
    if t:
        tid = t["targetId"]
        ctl.update_gateway_target(gatewayIdentifier=gid, targetId=tid, name=name, targetConfiguration=cfg,
                                  credentialProviderConfigurations=creds)
        print(f"   target {name} updated")
    else:
        tid = ctl.create_gateway_target(gatewayIdentifier=gid, name=name, targetConfiguration=cfg,
                                        credentialProviderConfigurations=creds,
                                        description=f"CampusMate {name} tool")["targetId"]
        print(f"   target {name} created")
    wait(lambda: ctl.get_gateway_target(gatewayIdentifier=gid, targetId=tid)["status"], ok=("READY",),
         bad=("FAILED", "UPDATE_UNSUCCESSFUL", "SYNCHRONIZE_UNSUCCESSFUL"), what=f"target {name}", every=5)
    return tid


def stage_gateway():
    step("AgentCore Gateway (inbound auth: AWS_IAM)")
    role = config.get_resource("gateway_role_arn") or iam.get_role(RoleName=N["gateway_role"])["Role"]["Arn"]
    g = find(ctl.list_gateways, "items", N["gateway"])
    if g and g.get("status") == "FAILED":   # self-heal a failed earlier attempt
        reasons = ctl.get_gateway(gatewayIdentifier=g["gatewayId"]).get("statusReasons")
        print(f"   gateway {g['gatewayId']} is FAILED ({reasons}); deleting and recreating")
        ctl.delete_gateway(gatewayIdentifier=g["gatewayId"])
        wait(lambda: (find(ctl.list_gateways, "items", N["gateway"]) or {}).get("status", "GONE"), ok=("GONE",),
             bad=(), what="failed gateway deletion", every=5)
        g = None
    if g:
        gid = g["gatewayId"]
        print(f"   gateway {gid} exists")
    else:
        gid = ctl.create_gateway(name=N["gateway"], roleArn=role, protocolType="MCP", authorizerType="AWS_IAM",
                                 description="CampusMate tools gateway (workshop)", exceptionLevel="DEBUG",
                                 tags=TAGS)["gatewayId"]
        print(f"   gateway {gid} created")
    wait(lambda: ctl.get_gateway(gatewayIdentifier=gid)["status"], ok=("READY",), what="gateway", every=5)
    gw = ctl.get_gateway(gatewayIdentifier=gid)
    config.save_resource("gateway_id", gid)
    config.save_resource("gateway_arn", gw["gatewayArn"])
    config.save_resource("gateway_url", gw["gatewayUrl"])
    a = config.get_resource("attendance_lambda_arn") or lam.get_function(FunctionName=N["attendance_lambda"])["Configuration"]["FunctionArn"]
    b = config.get_resource("leave_lambda_arn") or lam.get_function(FunctionName=N["leave_lambda"])["Configuration"]["FunctionArn"]
    t1 = ensure_target(gid, N["attendance_target"], a, load_schema("check_attendance_eligibility"))
    t2 = ensure_target(gid, N["leave_target"], b, load_schema("submit_leave_request"))
    config.save_resource("gateway_target_ids", [t1, t2])
    print(f"   gateway URL: {gw['gatewayUrl']}")


# ----------------------------------------------------------------------------
# policy
# ----------------------------------------------------------------------------
def caller_principal_id():
    """Cedar sees IAM callers as AgentCore::IamEntity; id = IAM user ARN or arn:aws:sts::<acct>:assumed-role/<role>."""
    arn = sts.get_caller_identity()["Arn"]
    if ":assumed-role/" in arn:
        role = arn.split(":assumed-role/")[1].split("/")[0]
        return f"arn:aws:sts::{ACCOUNT}:assumed-role/{role}"
    return arn


def baseline_policy(gateway_arn):
    agent = f"arn:aws:sts::{ACCOUNT}:assumed-role/{N['runtime_role']}"
    me = caller_principal_id()
    return ("// Baseline: the engine denies everything by default. Permit the CampusMate tools on THIS\n"
            "// gateway, but only for two callers: the agent's Runtime role and the student who deployed it.\n"
            "permit(\n  principal is AgentCore::IamEntity,\n  action,\n"
            f'  resource == AgentCore::Gateway::"{gateway_arn}"\n)\nwhen {{\n'
            f'  principal.id == "{agent}" ||\n  principal.id == "{me}"\n}};')


def ensure_policy(engine_id, name, statement, description):
    # Service quirk (Nov 2026): a CreatePolicy denied by IAM can leave its name reserved on the gateway
    # ("already exists" but not listed). We then fall back to name_v2 / name_v3, and look for those too.
    candidates = [name, f"{name}_v2", f"{name}_v3"]
    p = next((x for x in (find(ctl.list_policies, "policies", c, policyEngineId=engine_id) for c in candidates) if x), None)
    definition = {"cedar": {"statement": statement}}
    if p and p.get("status") in ("CREATE_FAILED", "UPDATE_FAILED"):
        print(f"   policy {name} is {p['status']}; deleting and recreating")
        ctl.delete_policy(policyEngineId=engine_id, policyId=p["policyId"])
        time.sleep(5)
        p = None
    if p:
        pid = p["policyId"]
        try:
            ctl.update_policy(policyEngineId=engine_id, policyId=pid, definition=definition,
                              description={"optionalValue": description})
            print(f"   policy {name} updated")
        except ClientError as e:
            print(f"   policy {name} update skipped: {e.response['Error']['Message'][:150]}")
    else:
        for cand in candidates:
            try:
                pid = ctl.create_policy(policyEngineId=engine_id, name=cand, definition=definition,
                                        description=description, validationMode="FAIL_ON_ANY_FINDINGS")["policyId"]
                print(f"   policy {cand} created")
                break
            except ctl.exceptions.ConflictException:
                if cand == candidates[-1]:
                    raise
                print(f"   policy name {cand} is reserved by an earlier failed attempt; trying the next name")
    try:
        wait(lambda: ctl.get_policy(policyEngineId=engine_id, policyId=pid)["status"], ok=("ACTIVE",),
             bad=("CREATE_FAILED", "UPDATE_FAILED", "FAILED"), what=f"policy {name}", every=3)
    except RuntimeError:
        reasons = ctl.get_policy(policyEngineId=engine_id, policyId=pid).get("statusReasons", [])
        print("   Cedar validation findings:\n    - " + "\n    - ".join(reasons))
        raise
    return pid


def stage_policy(mode="ENFORCE"):
    step(f"Policy engine + Cedar policies (attach in {mode} mode)")
    gid, garn = config.get_resource("gateway_id"), config.get_resource("gateway_arn")
    if not gid:
        sys.exit("Run the gateway stage first.")
    e = find(ctl.list_policy_engines, "policyEngines", N["policy_engine"])
    if e:
        eid = e["policyEngineId"]
        print(f"   policy engine {eid} exists")
    else:
        eid = ctl.create_policy_engine(name=N["policy_engine"], description="CampusMate governance (workshop)",
                                       tags=TAGS)["policyEngineId"]
        print(f"   policy engine {eid} created")
    wait(lambda: ctl.get_policy_engine(policyEngineId=eid)["status"], ok=("ACTIVE",), what="policy engine", every=3)
    earn = ctl.get_policy_engine(policyEngineId=eid)["policyEngineArn"]
    config.save_resource("policy_engine_id", eid)
    config.save_resource("policy_engine_arn", earn)
    leave = (ROOT / "projects" / "policies" / "leave_limit.cedar").read_text().replace("{{GATEWAY_ARN}}", garn)
    p1 = ensure_policy(eid, "allow_campus_tools", baseline_policy(garn), "Allow CampusMate tools on this gateway")
    p2 = ensure_policy(eid, "leave_limit", leave, "Deny leave requests longer than 3 days")
    config.save_resource("policy_ids", [p1, p2])
    gw = ctl.get_gateway(gatewayIdentifier=gid)
    current = gw.get("policyEngineConfiguration") or {}
    if current.get("arn") == earn and current.get("mode") == mode:
        print(f"   gateway already uses this engine in {mode} mode")
    else:
        ctl.update_gateway(gatewayIdentifier=gid, name=gw["name"], roleArn=gw["roleArn"],
                           protocolType=gw["protocolType"], authorizerType=gw["authorizerType"],
                           exceptionLevel=gw.get("exceptionLevel", "DEBUG"),
                           policyEngineConfiguration={"arn": earn, "mode": mode})
        print(f"   gateway attached to policy engine ({mode})")
        wait(lambda: ctl.get_gateway(gatewayIdentifier=gid)["status"], ok=("READY",), what="gateway", every=5)


# ----------------------------------------------------------------------------
# runtime: package for ARM64 Linux, upload to S3, create/update
# ----------------------------------------------------------------------------
RUNTIME_DEPS = [
    "strands-agents==1.64.0",
    "bedrock-agentcore==1.25.4",
    "mcp-proxy-for-aws==1.8.0",
    "aws-opentelemetry-distro==0.22.0",
    "boto3==1.43.126",
]


def build_package():
    build = ROOT / "projects" / ".build"
    deps_dir = build / "deps"
    stamp = build / "deps.sha"
    want = hashlib.sha256("\n".join(RUNTIME_DEPS).encode()).hexdigest()
    if not (deps_dir.is_dir() and stamp.exists() and stamp.read_text() == want):
        print("   downloading ARM64 Linux wheels (first time takes 1-2 minutes)...")
        shutil.rmtree(deps_dir, ignore_errors=True)
        deps_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                        "--platform", "manylinux2014_aarch64", "--implementation", "cp", "--python-version", "3.12",
                        "--only-binary=:all:", "--target", str(deps_dir), *RUNTIME_DEPS], check=True)
        stamp.write_text(want)
    else:
        print("   reusing cached ARM64 wheels")
    zpath = build / "campusmate_runtime.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        def add(path: Path, arc: str):
            info = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if os.access(path, os.X_OK) else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
        for p in sorted(deps_dir.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                add(p, p.relative_to(deps_dir).as_posix())
        add(ROOT / "projects" / "campusmate_agent.py", "campusmate_agent.py")
        for p in sorted((ROOT / "data").glob("*.json")):
            add(p, f"data/{p.name}")
    print(f"   package {zpath.name}: {zpath.stat().st_size / 1e6:.1f} MB")
    return zpath


def ensure_bucket():
    name = config.bucket_name(ACCOUNT)
    try:
        s3.head_bucket(Bucket=name, ExpectedBucketOwner=ACCOUNT)
    except ClientError:
        args = {"Bucket": name}
        if R != "us-east-1":
            args["CreateBucketConfiguration"] = {"LocationConstraint": R}
        s3.create_bucket(**args)
        s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
        s3.put_bucket_tagging(Bucket=name, Tagging={"TagSet": TAG_LIST})
        print(f"   bucket {name} created")
    config.save_resource("bucket", name)
    return name


def runtime_env():
    env = {"STUDENT_ID": SID, "MODEL_ID": config.MODEL_ID, "MAX_TOKENS": str(config.MAX_TOKENS),
           "UNIFIED_TRACES_DESTINATION_ENABLED": "true"}
    for key in ("memory_id", "gateway_url"):
        if config.load_resources()["resources"].get(key):
            env[key.upper()] = config.load_resources()["resources"][key]
    return env


def stage_runtime():
    step("AgentCore Runtime (direct code deployment, Python 3.12, ARM64)")
    zpath = build_package()
    bucket = ensure_bucket()
    key = f"{N['runtime']}/campusmate_runtime.zip"
    s3.upload_file(str(zpath), bucket, key, ExtraArgs={"ExpectedBucketOwner": ACCOUNT})
    artifact = {"codeConfiguration": {
        "code": {"s3": {"bucket": bucket, "prefix": key}},
        "runtime": config.PYTHON_RUNTIME,
        "entryPoint": ["opentelemetry-instrument", "campusmate_agent.py"]}}
    role = config.get_resource("runtime_role_arn") or iam.get_role(RoleName=N["runtime_role"])["Role"]["Arn"]
    env = runtime_env()
    print(f"   features: memory={'MEMORY_ID' in env} gateway={'GATEWAY_URL' in env}")
    common = dict(agentRuntimeArtifact=artifact, roleArn=role, networkConfiguration={"networkMode": "PUBLIC"},
                  environmentVariables=env, protocolConfiguration={"serverProtocol": "HTTP"},
                  lifecycleConfiguration={"idleRuntimeSessionTimeout": 900, "maxLifetime": 3600})
    rt = find(ctl.list_agent_runtimes, "agentRuntimes", N["runtime"], name_field="agentRuntimeName")
    if rt and rt.get("status") == "CREATE_FAILED":   # self-heal a failed earlier attempt
        print(f"   runtime {rt['agentRuntimeId']} is CREATE_FAILED; deleting and recreating")
        ctl.delete_agent_runtime(agentRuntimeId=rt["agentRuntimeId"])
        wait(lambda: (find(ctl.list_agent_runtimes, "agentRuntimes", N["runtime"], name_field="agentRuntimeName") or {}).get("status", "GONE"),
             ok=("GONE",), bad=(), what="failed runtime deletion", every=5)
        rt = None
    if rt:
        rid = rt["agentRuntimeId"]
        ctl.update_agent_runtime(agentRuntimeId=rid, description="CampusMate reference agent", **common)
        print(f"   runtime {rid} updated (new version)")
    else:
        for attempt in range(6):
            try:
                rid = ctl.create_agent_runtime(agentRuntimeName=N["runtime"], description="CampusMate reference agent",
                                               tags=TAGS, **common)["agentRuntimeId"]
                break
            except ClientError as e:
                if "role" not in str(e).lower() or attempt == 5:
                    raise
                print("   role not assumable yet, retrying in 10s")
                time.sleep(10)
        print(f"   runtime {rid} created")
    wait(lambda: ctl.get_agent_runtime(agentRuntimeId=rid)["status"], ok=("READY",),
         bad=("CREATE_FAILED", "UPDATE_FAILED"), what="runtime", every=10)
    info = ctl.get_agent_runtime(agentRuntimeId=rid)
    config.save_resource("agent_runtime_id", rid)
    config.save_resource("agent_runtime_arn", info["agentRuntimeArn"])
    config.save_resource("runtime_log_group", f"/aws/bedrock-agentcore/runtimes/{rid}-DEFAULT")


# ----------------------------------------------------------------------------
# eval
# ----------------------------------------------------------------------------
EVALUATORS = ["Builtin.GoalSuccessRate", "Builtin.Helpfulness", "Builtin.ToolSelectionAccuracy"]


def stage_eval():
    step("Online evaluation (LLM-as-a-judge on live traffic)")
    rid = config.get_resource("agent_runtime_id")
    if not rid:
        sys.exit("Run the runtime stage first.")
    role = config.get_resource("eval_role_arn") or iam.get_role(RoleName=N["eval_role"])["Role"]["Arn"]
    existing = find(ctl.list_online_evaluation_configs, "onlineEvaluationConfigs", N["online_eval"],
                    name_field="onlineEvaluationConfigName")
    if existing:
        oid = existing["onlineEvaluationConfigId"]
        print(f"   online evaluation {oid} exists")
    else:
        oid = ctl.create_online_evaluation_config(
            onlineEvaluationConfigName=N["online_eval"],
            description="CampusMate built-in evaluators (workshop)",
            rule={"samplingConfig": {"samplingPercentage": 100.0}, "sessionConfig": {"sessionTimeoutMinutes": 5}},
            dataSourceConfig={"cloudWatchLogs": {"logGroupNames": [f"/aws/bedrock-agentcore/runtimes/{rid}-DEFAULT"],
                                                 "serviceNames": [f"{N['runtime']}.DEFAULT"]}},
            evaluators=[{"evaluatorId": e} for e in EVALUATORS],
            evaluationExecutionRoleArn=role, enableOnCreate=True, tags=TAGS)["onlineEvaluationConfigId"]
        print(f"   online evaluation {oid} created")
    wait(lambda: ctl.get_online_evaluation_config(onlineEvaluationConfigId=oid)["status"],
         ok=("ACTIVE",), bad=("CREATE_FAILED", "FAILED"), what="online evaluation", every=5)
    cfg = ctl.get_online_evaluation_config(onlineEvaluationConfigId=oid)
    config.save_resource("online_eval_id", oid)
    config.save_resource("online_eval_arn", cfg.get("onlineEvaluationConfigArn"))
    out = (cfg.get("outputConfig") or {}).get("cloudWatchConfig", {}).get("logGroupName")
    config.save_resource("eval_results_log_group", out or f"/aws/bedrock-agentcore/evaluations/results/{oid}")


FUNCS = {"observability": stage_observability, "roles": stage_roles, "lambdas": stage_lambdas,
         "memory": stage_memory, "gateway": stage_gateway, "policy": stage_policy,
         "runtime": stage_runtime, "eval": stage_eval}
t0 = time.time()
for s in ALL:
    if s in STAGES:
        FUNCS[s]()
print(f"\n== Done in {time.time() - t0:.0f}s. Resources recorded in projects/.deployed-resources.json")
arn = config.load_resources()["resources"].get("agent_runtime_arn")
if arn:
    print(f"== Agent ARN: {arn}")
PYEOF
