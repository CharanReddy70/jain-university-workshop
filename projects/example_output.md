# Example output: what a healthy run looks like

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

Real output captured on 8 November 2026 (us-east-1, `STUDENT_ID=instructor`). IDs and timings will differ for you.

## `bash projects/deploy.sh` (first run, ~5 minutes)

```
== CampusMate deploy | python: .../.venv/bin/python | stages: all
   account 123456789012 | region us-east-1 | student instructor | model us.anthropic.claude-sonnet-5-5

-- Observability: CloudWatch Transaction Search
   already enabled (ACTIVE) - nothing to do
-- IAM roles (least privilege, scoped to this student's resources)
   role campusmate-runtime-role-instructor created
   role campusmate-lambda-role-instructor created
   role campusmate-gateway-role-instructor created
   role campusmate-eval-role-instructor created
-- Lambda tools
   lambda campusmate-attendance-instructor created
   lambda campusmate-leave-instructor created
-- AgentCore Memory
   memory campusmate_mem_instructor-F32IDE9msK created (takes 1-3 minutes to become ACTIVE)
-- AgentCore Gateway (inbound auth: AWS_IAM)
   gateway campusmate-gw-instructor-zhox6xxi08 created
   target attendance created
   target leave created
   gateway URL: https://campusmate-gw-instructor-zhox6xxi08.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
-- Policy engine + Cedar policies (attach in ENFORCE mode)
   policy engine campusmate_pe_instructor-97eb6v4w95 created
   policy allow_campus_tools created
   policy leave_limit created
   gateway attached to policy engine (ENFORCE)
-- AgentCore Runtime (direct code deployment, Python 3.12, ARM64)
   downloading ARM64 Linux wheels (first time takes 1-2 minutes)...
   package campusmate_runtime.zip: 50.0 MB
   bucket campusmate-instructor-123456789012-us-east-1 created
   features: memory=True gateway=True
   runtime campusmate_instructor-Cz2RdT3pXu created
-- Online evaluation (LLM-as-a-judge on live traffic)
   online evaluation campusmate_eval_instructor-N0N1yaGgGv created

== Done in 312s. Resources recorded in projects/.deployed-resources.json
== Agent ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/campusmate_instructor-Cz2RdT3pXu
```
Running it again prints `exists` / `updated` instead of `created`: it is idempotent.

## `python scripts/05_agentcore_runtime.py`

```
Session A: Here's the fee late-payment rule:
- Tuition is Rs. 1,25,000 per semester. It's due by the 15th day of the semester.
- After the due date, a late fee of Rs. 500 per week applies.
- If fees stay pending for more than 30 days, your hall ticket for the semester-end exams is blocked.

Session A again: Your favourite subject is Computer Networks. You told me that in your first message.

Session B (new): I don't have any information about your favourite subject. ...
```

## `python scripts/11_governance.py`

```
2 days -> ALLOWED {"submitted":true,"reference":"LV-905240DE","student_id":"AIDD-DEMO-001","start_date":"2026-12-01","end_date":"2026-12-02","days":2,...}
5 days -> DENIED Tool Execution Denied: Tool call not allowed due to policy enforcement [Policy evaluation denied due to leave_limit-1a39hxipe9]
```

## Terminal chat: `python projects/campusmate_agent.py --chat --student AIDD-DEMO-003`

```
CampusMate (us.anthropic.claude-sonnet-5-5) | student AIDD-DEMO-003 | memory=True gateway=True
You: Am I eligible to write the AIDD303 exam?
   [tool] attendance___check_attendance_eligibility({"student_id": "AIDD-DEMO-003", "course_code": "AIDD303"}) -> success
CampusMate: No, Rohan, you're not eligible right now.
- AIDD303 attendance: 74%. The minimum is 75%, so you're 1% short. ...
```

## `python scripts/10_evaluations.py` (online evaluation scores)

```
campusmate_eval_instructor ACTIVE ENABLED ['Builtin.GoalSuccessRate', 'Builtin.Helpfulness', 'Builtin.ToolSelectionAccuracy'] sampling 100.0%
 - Builtin.GoalSuccessRate          score=1.0  The user had two goals: (1) get info about their favourite subject (Computer Networks) and
 - Builtin.Helpfulness              score=0.83  The user's main goal was to learn the fee late-payment rule, with a mention of their favou
 - Builtin.ToolSelectionAccuracy    score=1.0  Step 1: There are no earlier tool calls in this conversation; this is the first action tak
 - Builtin.GoalSuccessRate          score=0.0  The User's goal was to file 5 days of leave for AIDD-DEMO-001 starting 2026-12-01. The ass
```
(The last line is a prompt-injection attempt that CampusMate correctly refused: the judge scores the *user's* goal, not your rules.)

## `bash scripts/smoke_test.sh` (summary)

See TEST_REPORT.md for the full, current run. A healthy run ends with:
```
== 13 passed, 0 failed, 1 warnings
```
(the warning is "online evaluation has scored sessions", which lags 15-30 minutes behind fresh traffic).
