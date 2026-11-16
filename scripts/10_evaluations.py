"""
Module 10 live demo: online evaluation = an LLM judge scoring live sessions. Show the
config and the latest scores from the results log group.
Run: python scripts/10_evaluations.py
"""
import json
import boto3

STUDENT_ID, REGION = "instructor", "us-east-1"
ctl, logs = boto3.client("bedrock-agentcore-control", region_name=REGION), boto3.client("logs", region_name=REGION)
cfg = next(c for c in ctl.list_online_evaluation_configs()["onlineEvaluationConfigs"]
           if c["onlineEvaluationConfigName"] == f"campusmate_eval_{STUDENT_ID}")
oid = cfg["onlineEvaluationConfigId"]
cfg = ctl.get_online_evaluation_config(onlineEvaluationConfigId=oid)
print(cfg["onlineEvaluationConfigName"], cfg["status"], cfg.get("executionStatus"),
      [e["evaluatorId"] for e in cfg["evaluators"]], f"sampling {cfg['rule']['samplingConfig']['samplingPercentage']}%")
pages = logs.get_paginator("filter_log_events").paginate(logGroupName=f"/aws/bedrock-agentcore/evaluations/results/{oid}",
                                                          PaginationConfig={"MaxItems": 10})
for ev in (e for page in pages for e in page["events"]):   # paginate: pages can be empty while CloudWatch scans
    a = json.loads(ev["message"]).get("attributes", {})
    print(f" - {a.get('gen_ai.evaluation.name', '?'):32s} score={a.get('gen_ai.evaluation.score.value', '?')}  "
          f"{str(a.get('gen_ai.evaluation.explanation', ''))[:90]}")
