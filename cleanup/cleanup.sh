#!/usr/bin/env bash
# =============================================================================
# CampusMate cleanup - delete EVERYTHING deploy.sh / the notebooks created for
# your STUDENT_ID, in dependency order, then prove nothing is left.
#
# Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer
# Science and Engineering, Jain (Deemed-to-be University), Bengaluru.
#
# Usage (repo root):   bash cleanup/cleanup.sh priya07          # your student ID; asks for confirmation
#                      bash cleanup/cleanup.sh priya07 --yes    # no prompt
#                      bash cleanup/cleanup.sh                  # uses STUDENT_ID from .env (instructor)
#
# It reads projects/.deployed-resources.json AND looks resources up by their
# per-student names, so it still works if the file is missing or a deploy
# stopped half way. It only ever touches resources whose names contain your
# STUDENT_ID. Running it twice is harmless.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "$ROOT/.venv/bin/python" ]]; then PY="$ROOT/.venv/bin/python";
elif [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then PY="$ROOT/.venv/Scripts/python.exe";
else PY="${PYTHON:-python3}"; fi
cd "$ROOT"
if [[ $# -gt 0 && "$1" != --* ]]; then export STUDENT_ID="$1"; shift; fi
exec "$PY" -u - "$@" <<'PYEOF'
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "projects"))
import config
import boto3
from botocore.exceptions import ClientError

R, N, SID = config.REGION, config.NAMES, config.SID
reg = config.load_resources()["resources"]
if "--yes" not in sys.argv:
    ans = input(f"Delete ALL CampusMate resources for STUDENT_ID='{SID}' in {R}? Type the student ID to confirm: ")
    if ans.strip().lower() != SID:
        sys.exit("Cancelled.")

s = boto3.Session(region_name=R)
ACCOUNT = s.client("sts").get_caller_identity()["Account"]
ctl, lam, iam, s3, logs = (s.client(x) for x in ("bedrock-agentcore-control", "lambda", "iam", "s3", "logs"))
problems = []


def safe(desc, fn, *a, **kw):
    try:
        fn(*a, **kw)
        print(f"   deleted {desc}")
        return True
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("ResourceNotFoundException", "NoSuchEntity", "NoSuchBucket", "404", "NotFound"):
            print(f"   {desc}: already gone")
        else:
            print(f"   {desc}: {code} {e.response['Error']['Message'][:160]}")
            problems.append(desc)
        return False


def gone(fn, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            fn()
        except ClientError as e:
            if e.response["Error"]["Code"] in ("ResourceNotFoundException",):
                return True
            raise
        time.sleep(5)
    return False


def all_items(fn, key, **kw):
    out, token = [], None
    while True:
        resp = fn(**({**kw, "nextToken": token} if token else kw))
        out += resp.get(key, [])
        token = resp.get("nextToken")
        if not token:
            return out


print(f"== Cleaning up CampusMate for student '{SID}' in {R} (account {ACCOUNT})")

print("\n-- 0. The AgentCore CLI project (notebooks 05-12): one CloudFormation stack")
cfn = s.client("cloudformation")
CLI_STACK = f"AgentCore-campusmate{SID}-default"
try:
    cfn.describe_stacks(StackName=CLI_STACK)
    cfn.delete_stack(StackName=CLI_STACK)
    print(f"   deleting stack {CLI_STACK} (runtime, memory, gateway, policies, evaluation)... this can take several minutes")
    try:
        cfn.get_waiter("stack_delete_complete").wait(StackName=CLI_STACK, WaiterConfig={"Delay": 20, "MaxAttempts": 60})
        print(f"   deleted stack {CLI_STACK}")
    except Exception as e:  # noqa: BLE001
        print(f"   stack {CLI_STACK} still deleting or failed: {str(e)[:150]}")
        problems.append(f"stack {CLI_STACK}")
except ClientError:
    print(f"   no CLI project stack {CLI_STACK}: nothing to do")

print("\n-- 1. Online evaluation")
evals = {reg.get("online_eval_id")} | {e["onlineEvaluationConfigId"] for e in all_items(
    ctl.list_online_evaluation_configs, "onlineEvaluationConfigs") if e["onlineEvaluationConfigName"] == N["online_eval"]}
for oid in filter(None, evals):
    safe(f"online evaluation {oid}", ctl.delete_online_evaluation_config, onlineEvaluationConfigId=oid)

print("\n-- 1b. Prompt recommendations (instructor demo, scripts/12)")
dpl = s.client("bedrock-agentcore")
try:
    for r in all_items(dpl.list_recommendations, "recommendationSummaries"):
        if r.get("name", "").startswith(f"campusmate_prompt_{SID}_"):
            safe(f"recommendation {r['recommendationId']}", dpl.delete_recommendation, recommendationId=r["recommendationId"])
except ClientError as e:
    print(f"   recommendations: skipped ({e.response['Error']['Code']})")

print("\n-- 2. AgentCore Runtime")
rts = {reg.get("agent_runtime_id")} | {r["agentRuntimeId"] for r in all_items(ctl.list_agent_runtimes, "agentRuntimes")
                                       if r["agentRuntimeName"] == N["runtime"]}
for rid in filter(None, rts):
    if safe(f"runtime {rid}", ctl.delete_agent_runtime, agentRuntimeId=rid):
        gone(lambda: ctl.get_agent_runtime(agentRuntimeId=rid))

print("\n-- 3. Gateway targets and Gateway")
gws = {reg.get("gateway_id")} | {g["gatewayId"] for g in all_items(ctl.list_gateways, "items") if g["name"] == N["gateway"]}
for gid in filter(None, gws):
    try:
        for t in all_items(ctl.list_gateway_targets, "items", gatewayIdentifier=gid):
            if safe(f"gateway target {t['name']}", ctl.delete_gateway_target, gatewayIdentifier=gid, targetId=t["targetId"]):
                gone(lambda: ctl.get_gateway_target(gatewayIdentifier=gid, targetId=t["targetId"]), 180)
    except ClientError:
        pass
    if safe(f"gateway {gid}", ctl.delete_gateway, gatewayIdentifier=gid):
        gone(lambda: ctl.get_gateway(gatewayIdentifier=gid))

print("\n-- 4. Cedar policies and policy engine")
engines = {reg.get("policy_engine_id")} | {e["policyEngineId"] for e in all_items(ctl.list_policy_engines, "policyEngines")
                                          if e["name"] == N["policy_engine"]}
for eid in filter(None, engines):
    try:
        for p in all_items(ctl.list_policies, "policies", policyEngineId=eid):
            if safe(f"policy {p['name']}", ctl.delete_policy, policyEngineId=eid, policyId=p["policyId"]):
                gone(lambda: ctl.get_policy(policyEngineId=eid, policyId=p["policyId"]), 120)
    except ClientError:
        pass
    if safe(f"policy engine {eid}", ctl.delete_policy_engine, policyEngineId=eid):
        gone(lambda: ctl.get_policy_engine(policyEngineId=eid), 180)

print("\n-- 5. AgentCore Memory (all stored memories are deleted too)")
all_mems = {m["id"]: m.get("status") for m in all_items(ctl.list_memories, "memories")}
mems = {reg.get("memory_id")} | {mid for mid in all_mems if mid.startswith(N["memory"] + "-")}
for mid in filter(None, mems):
    if all_mems.get(mid) == "DELETING":
        print(f"   memory {mid}: already being deleted")
        continue
    safe(f"memory {mid}", ctl.delete_memory, memoryId=mid)

print("\n-- 6. Lambda functions")
for fn in (N["attendance_lambda"], N["leave_lambda"], f"campusmate-capstone-{SID}"):  # capstone = notebook 12
    safe(f"lambda {fn}", lam.delete_function, FunctionName=fn)

print("\n-- 7. S3 code bucket")
bucket = reg.get("bucket") or config.bucket_name(ACCOUNT)
try:
    objs = s3.list_object_versions(Bucket=bucket)
    for o in objs.get("Versions", []) + objs.get("DeleteMarkers", []):
        s3.delete_object(Bucket=bucket, Key=o["Key"], VersionId=o["VersionId"])
    safe(f"bucket {bucket}", s3.delete_bucket, Bucket=bucket)
except ClientError as e:
    print(f"   bucket {bucket}: already gone" if "NoSuchBucket" in str(e) or "404" in str(e) else f"   bucket: {e}")

print("\n-- 8. IAM roles")
for key in ("runtime_role", "gateway_role", "lambda_role", "eval_role"):
    role = N[key]
    try:
        for p in iam.list_role_policies(RoleName=role)["PolicyNames"]:
            iam.delete_role_policy(RoleName=role, PolicyName=p)
        for p in iam.list_attached_role_policies(RoleName=role)["AttachedPolicies"]:
            iam.detach_role_policy(RoleName=role, PolicyArn=p["PolicyArn"])
    except ClientError:
        pass
    safe(f"role {role}", iam.delete_role, RoleName=role)

print("\n-- 9. CloudWatch log groups")
groups = {f"/aws/lambda/{N['attendance_lambda']}", f"/aws/lambda/{N['leave_lambda']}", f"/aws/lambda/campusmate-capstone-{SID}"}
for rid in filter(None, rts):
    groups.add(f"/aws/bedrock-agentcore/runtimes/{rid}-DEFAULT")
for oid in filter(None, evals):
    groups.add(f"/aws/bedrock-agentcore/evaluations/results/{oid}")
if reg.get("eval_results_log_group"):
    groups.add(reg["eval_results_log_group"])
for prefix in (f"/aws/bedrock-agentcore/runtimes/{N['runtime']}-", "/aws/bedrock-agentcore/evaluations/results/" + N["online_eval"],
               f"/aws/bedrock-agentcore/runtimes/campusmate{SID}_default_", f"/aws/bedrock-agentcore/evaluations/results/campusmate{SID}_"):
    for g in logs.describe_log_groups(logGroupNamePrefix=prefix).get("logGroups", []):
        groups.add(g["logGroupName"])
for g in sorted(groups):
    try:
        logs.delete_log_group(logGroupName=g)
        print(f"   deleted log group {g}")
    except ClientError:
        pass

if config.RESOURCES_FILE.exists():
    config.RESOURCES_FILE.unlink()
    print("\n   removed projects/.deployed-resources.json")

print("\n== Verification: anything tagged project=campusmate-workshop, student=%s ?" % SID)
time.sleep(5)
tagged = []
for page in s.client("resourcegroupstaggingapi").get_paginator("get_resources").paginate(
        TagFilters=[{"Key": "project", "Values": ["campusmate-workshop"]}, {"Key": "student", "Values": [SID]}]):
    tagged += [m["ResourceARN"] for m in page["ResourceTagMappingList"]]
left = []
for arn in tagged:  # the tagging index can lag a few minutes; double-check each ARN really exists
    if ":memory/" in arn and any(m["id"] in arn and m.get("status") != "DELETING" for m in all_items(ctl.list_memories, "memories")):
        left.append(arn)
    elif ":memory/" not in arn:
        left.append(arn)
roles_left = []
for key in ("runtime_role", "gateway_role", "lambda_role", "eval_role"):
    try:
        iam.get_role(RoleName=N[key])
        roles_left.append(N[key])
    except ClientError:
        pass
names_left = [r["agentRuntimeName"] for r in all_items(ctl.list_agent_runtimes, "agentRuntimes")
              if r["agentRuntimeName"] in (N["runtime"], f"campusmate{SID}_default_agent")]
names_left += [g["name"] for g in all_items(ctl.list_gateways, "items") if g["name"] == N["gateway"]]
names_left += [m["id"] for m in all_items(ctl.list_memories, "memories")
               if m["id"].startswith(N["memory"] + "-") and m.get("status") != "DELETING"]
print(f"   tagged resources (tagging index, may lag ~minutes): {tagged or 'none'}")
print(f"   IAM roles left: {roles_left or 'none'}")
print(f"   AgentCore resources left by name: {names_left or 'none'}")
really_left = [a for a in left if not any(x in a for x in (":runtime/", ":gateway/", ":policy-engine/", ":online-evaluation-config/"))]
if roles_left or names_left or problems:
    print(f"\nFAIL: something is left ({problems}). Re-run this script in a minute.")
    sys.exit(1)
if really_left:
    print("\nNOTE: the tagging index still lists some ARNs (it lags behind deletes). They no longer exist by name.")
print("\nPASS: nothing for this STUDENT_ID remains. Thanks for cleaning up!")
PYEOF
