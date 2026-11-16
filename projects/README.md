# projects/: the finished CampusMate system

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

This folder is the **reference solution**: everything the notebooks build, wired together and deployable with one command.
If you fall behind in a lab, copy from here (each notebook's Checkpoint tells you which file).

## Files

| File | What it is |
|---|---|
| `config.py` | Settings for the **instructor tools only** (`deploy.sh`, `smoke_test.sh`, `cleanup.sh`): region, models, per-student names from `.env`, and the `.deployed-resources.json` registry. Students never need it; the agent, the web app and the notebooks have their settings written at the top. |
| `campusmate_agent.py` | The final agent (settings at the top; memory and gateway switch on via the `MEMORY_ID` / `GATEWAY_URL` environment variables): local tools (`get_course_info`, `get_campus_policy`), Gateway tools over MCP (SigV4), AgentCore Memory session manager, and the AgentCore Runtime entrypoint. Runs locally (`--chat`) and on Runtime. |
| `deploy.sh` | **Instructor-only.** One-command, idempotent deploy of the whole system for one `STUDENT_ID` (stages: observability, roles, lambdas, memory, gateway, policy, runtime, eval). Used for rehearsal, the fallback agent, and catching up a student. Students build the same things step by step in notebooks 05-11. |
| `lambda/check_attendance_eligibility/` | Lambda tool: attendance per course vs the 75% placeholder rule, hall-ticket eligibility. `tool_schema.json` is the MCP tool schema. |
| `lambda/submit_leave_request/` | The governed action: files a leave request (stateless, returns a confirmation). It does **not** enforce the limit itself. |
| `policies/leave_limit.cedar` | Cedar policy: forbid leave requests above 3 days at the Gateway. |
| `web/` | Flask chat portal (`app.py`, `templates/`, `static/`). Put your ID in `STUDENT_ID` at the top of `app.py`. No login; a dropdown picks the fictional student (= Memory actor ID). |
| `injection_attempts.md` | Ten prompt-injection attacks for Lab 11. |
| `example_output.md` | What a healthy run looks like (deploy, chat, smoke test). |
| `.deployed-resources.json` | *(created by `deploy.sh`, git-ignored)* every ARN/ID it created; cleanup also finds resources by name, so it works without this file. |

## Run it

```bash
python projects/campusmate_agent.py --chat                      # local, uses whatever is deployed (memory/gateway) automatically
python projects/campusmate_agent.py --chat --student AIDD-DEMO-003
bash projects/deploy.sh                                         # instructor: deploy everything (~5 min first time)
python projects/web/app.py                                      # http://localhost:5050
bash scripts/smoke_test.sh                                      # verify end to end
bash cleanup/cleanup.sh                                         # remove everything
```

## The final system

```
Browser → Flask (projects/web) → AgentCore Runtime (campusmate_<id>)
                                   ├─ Amazon Bedrock via Strands (Amazon Nova 2 Lite)
                                   ├─ local tools: get_course_info, get_campus_policy  (data/*.json, bundled in the zip)
                                   ├─ AgentCore Memory (campusmate_mem_<id>): events + /students/{actor}/facts|summaries
                                   └─ AgentCore Gateway (campusmate-gw-<id>, AWS_IAM inbound)
                                        ├─ Policy engine (campusmate_pe_<id>, ENFORCE): allow_campus_tools + leave_limit
                                        ├─ target "attendance" → Lambda campusmate-attendance-<id>
                                        └─ target "leave"      → Lambda campusmate-leave-<id>
Observability: OpenTelemetry spans → /aws/bedrock-agentcore/runtimes/<id>-DEFAULT (CloudWatch, Transaction Search)
Evaluations:   online config campusmate_eval_<id> (GoalSuccessRate, Helpfulness, ToolSelectionAccuracy)
```

Feature switches: the agent turns Memory on when the environment variable `MEMORY_ID` is set, and Gateway tools on when
`GATEWAY_URL` is set (the Runtime gets them in Labs 6 and 7). That's how one file serves as v2, v3, v4 and v8.

## Tags and names

Every resource is named with your `STUDENT_ID` and tagged `project=campusmate-workshop`, `student=<STUDENT_ID>` (where the service supports tags).
