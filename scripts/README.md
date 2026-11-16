# Instructor guide: run-of-show, live demos and fallbacks

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

Each `scripts/NN_*.py` is a 10-25 line live demo for the module with the same number as `notebooks/NN-*.ipynb`. Run them from the
**repo root** with the venv active: `python scripts/05_agentcore_runtime.py`. Type them live if you like; they are short on purpose.
Settings are plain variables at the top of each script. Scripts 05-12 use `STUDENT_ID = "instructor"`, i.e. your own pre-deployed agent.

| Script | What it shows | Needs deployed system? |
|---|---|---|
| `check_setup.py` | One-command pre-flight: Python, packages, identity, region, model access, AgentCore | no |
| `01_genai_demos.py` | Hallucinated "Rule 42B", statelessness, temperature 0 vs 1 | no |
| `02_aws_identity_check.py` | Who am I, region, a deliberate `AccessDenied` and how to read it | no |
| `03_first_agent.py` | A 3-line agent, then a personality + remembered chat, then a first tool | no |
| `04_strands_tools.py` | Strands agent with two `@tool`s over `data/*.json` | no |
| `05_agentcore_runtime.py` | Same session remembers, new session doesn't | runtime |
| `06_agentcore_memory.py AIDD-DEMO-001` | Long-term records extracted for a student | memory |
| `07_gateway_lambda.py` | Gateway = MCP server: `tools/list`, call the attendance Lambda (74% vs 75%) | gateway |
| `08_customer_interface.py` | What the browser does, via Flask's test client | runtime |
| `09_observability.py` | Spans from CloudWatch: steps, latency, tokens | runtime + traffic |
| `10_evaluations.py` | Online evaluation config and latest judge scores | eval |
| `11_governance.py` | Cedar at the Gateway: 2 days ALLOWED, 5 days DENIED | policy |
| `12_continuous_improvement.py` | Instructor-only: AI-generated prompt recommendation (real call) + narrated Gateway A/B test | runtime + traffic |
| `smoke_test.sh` | End-to-end checks of the whole system | everything |
| `mcp.json` | Example MCP client config (from the original workshop) for local MCP servers | no |

---

## Pre-workshop checklist (do it 2-3 days before)

- [ ] **Account**: a sandbox AWS account just for the workshop; billing alerts set (AWS Budgets, for example US$300 with email alerts at 50/80/100%).
- [ ] **Region**: `us-east-1`. Confirm AgentCore is there: `aws bedrock-agentcore-control list-agent-runtimes --region us-east-1`.
- [ ] **Model access**: `python scripts/check_setup.py` passes as the instructor (it calls both models).
- [ ] **Quotas** (Service Quotas console → Amazon Bedrock): requests/tokens per minute for the Amazon Nova 2 Lite cross-region profile.
  40 students × ~3 calls per question can spike to ~100 requests/minute during labs. Request an increase a week ahead if the default is lower.
  AgentCore defaults (runtimes, gateways, memories per account) are well above 40 each, but check *Amazon Bedrock AgentCore* in Service Quotas.
- [ ] **Transaction Search** (account-level, once): `bash projects/deploy.sh observability`. The first spans in a new account can take ~10 minutes.
- [ ] **Student access**: one IAM user per student in an IAM group with the AWS-managed `AdministratorAccess` policy (see SETUP.md), access keys handed out privately. Use a separate sandbox account.
- [ ] **CDK bootstrap** (the AgentCore CLI deploys through AWS CDK): `cdk bootstrap aws://<ACCOUNT_ID>/us-east-1` once, or check the `CDKToolkit` stack exists. If the account is in an AWS Organization, check no SCP blocks `bedrock-agentcore:*`, CloudFormation or cross-region inference.
- [ ] **Laptop tools**: Python 3.10+, AWS CLI, **Node.js 20+, the AgentCore CLI (`npm install -g @aws/agentcore`) and uv**. `check_setup.py` checks all of them.
- [ ] **Pre-deploy your own copy** with `STUDENT_ID=instructor` in `.env`: `bash projects/deploy.sh && bash scripts/smoke_test.sh`. It's your demo agent for the 9:00 intro and the fallback for anyone stuck. Also run notebooks 05-12 once yourself with a test ID to rehearse.
- [ ] **Send SETUP.md** to students 3 days ahead; ask for a screenshot of `check_setup.py` passing.
- [ ] **Wi-Fi**: test that `pip install` and `*.amazonaws.com` work on the lab network; have a hotspot as plan B.
- [ ] Print the [assessment](../assessment/) quizzes or load them into a form; prepare certificates from `assessment/certificate-text.md`.

---

## Teaching rhythm (every lab)

Students are new to AWS, so nothing is deployed for them in one go, and the notebooks contain **no stage directions**: they read as
normal, self-explanatory labs. The rhythm is yours to run: each AWS step is a short markdown explanation followed by one code cell.
**Explain the markdown first** (analogy, what will be created, what could go wrong), then say **"run it now"**; everyone runs that one
cell and you wait until most screens show the expected output before moving on. Ask one student to read their output aloud. Keep the
"Your turn" exercises for the last 5-10 minutes of each lab.

## Day 1: build the agent (9:00 AM - 3:30 PM)

| Time | Block | Type | What to do and say |
|---|---|---|---|
| 9:00-9:05 | Welcome | talk | Who we are, what CampusMate is. **Show the finished portal** (your pre-deployed agent, `python projects/web/app.py`): ask "Am I eligible for my exams?" as AIDD-DEMO-003. "By tomorrow afternoon you will have built this yourself." |
| 9:05-9:25 | 01 GenAI foundations | theory | LLM = predicts next text (the senior who read every notice board). Tokens = what you pay for. Context window = answer-sheet size. Temperature. Hallucination. Statelessness. Thinking tokens (new in 2026). |
| 9:25-9:40 | 01 demos | demo | `python scripts/01_genai_demos.py`. Pause after Rule 42B: "Did it make it up or refuse? Either way, would you trust it with exam rules?" Then statelessness: "This is why chat apps resend everything." |
| 9:40-9:50 | 02 AWS essentials | theory | Account = college, IAM = ID cards, policy = which rooms your card opens, region = which campus. Why us-east-1. |
| 9:50-10:10 | 02 lab | lab | Students run notebook 02. Live: `python scripts/02_aws_identity_check.py`. Read the AccessDenied message aloud: WHO, WHAT action, NOT ALLOWED. Everyone runs `check_setup.py`. |
| 10:10-10:25 | 03 Your first Strands agent | theory | What an agent is: model + instructions + tools. Strands = the admission portal that talks to every office (Bedrock) for you. One model (Nova 2 Lite), tokens = money. |
| 10:25-10:45 | 03 lab (part 1) | lab | Notebook 03 Steps 1-4: type the 4-line agent together first, then personality, conversation, model choice. Live: `python scripts/03_first_agent.py`. |
| 10:45-11:00 | **Break** | | |
| 11:00-11:10 | 03 lab (part 2) | lab | Step 5 (cost) and Step 6 (first tool) + "Your turn". Ask one student to explain the 4-step tool loop in their own words. |
| 11:10-11:30 | 04 Strands tools | theory | Agent loop (reason, act, observe). `@tool` docstrings are advertisements to the model. From a toy tool to real ones that read the course list and rulebook. |
| 11:30-12:30 | 04 lab | lab | Notebook 04: build both tools, test in a loop, "Your turn" `get_event_info`. Live: `python scripts/04_strands_tools.py`. Walk the room. |
| 12:30-1:15 | **Lunch** | | Kick off nothing heavy; quotas reset per minute anyway. |
| 1:15-1:30 | 05 Runtime | theory | Prototype-to-production gap (cooking at home vs running the canteen). microVM per session, `/invocations` + `/ping`, 33-char session IDs. Why direct code deploy and not the deprecated starter toolkit. |
| 1:30-2:00 | 05 lab | lab | Notebook 05 step by step: `agentcore create` (1 min) → look at the starter `main.py` → write **their notebook-04 agent** + the 3-line wrapper into it → add libraries → `agentcore deploy` (2-3 min: explain role, packaging, Runtime while it runs) → `ask()` same session vs new session. Live: `python scripts/05_agentcore_runtime.py`. |
| 2:00-2:15 | 06 Memory | theory | Attendance register (short-term) vs department file (long-term). Semantic vs summary. Namespaces per actor. **Extraction is asynchronous**: say it twice. |
| 2:15-2:45 | 06 lab | lab | Notebook 06: `agentcore add memory`, the `# NEW in Lab 6` lines, deploy (2-4 min), tell a fact, wait for extraction (explain the polling cell while it runs), new session remembers. Live: `python scripts/06_agentcore_memory.py AIDD-DEMO-001`. |
| 2:45-3:00 | 07 MCP + Gateway | theory | MCP = USB-C for tools. Gateway = managed MCP server; `AWS_IAM` means only signed calls from our account. Tool names `target___tool`. |
| 3:00-3:25 | 07 lab | lab | Notebook 07: create the Lambda, `agentcore add gateway` + `add gateway-target`, the `# NEW in Lab 7` lines, deploy, direct MCP call (74% vs 75%), then ask the agent. Live: `python scripts/07_gateway_lambda.py`. |
| 3:25-3:30 | Wrap-up | talk | "Today: brain, tools, cloud home, memory, shared tools. Tomorrow: a face, X-ray vision, a report card and real rules." Leave everything deployed. |

## Day 2: make it production-ready (9:00 AM - 3:30 PM)

| Time | Block | Type | What to do and say |
|---|---|---|---|
| 9:00-9:15 | Recap + Day 1 quiz | quiz | `assessment/day1-quiz.md` (10 questions, 10 minutes). Go through the 3 most-missed answers. |
| 9:15-9:25 | 08 Customer interface | theory | Browser → Flask → Runtime; no login; dropdown = Memory actor; cookie = Runtime session; the fee-counter clerk analogy. |
| 9:25-10:00 | 08 lab | lab | Notebook 08, then everyone runs `python projects/web/app.py` and chats. "Chat with a classmate's agent" exercise: pairs swap ARNs. Live: `python scripts/08_customer_interface.py`. |
| 10:00-10:15 | 09 Observability | theory | Trace / span / log / metric (exam-day journey). Transaction Search is account-level (already on). Where cost comes from: input tokens grow every step. |
| 10:15-10:45 | 09 lab | lab | Notebook 09 + the **bad-answer recipe** (hackathon "apply leave" vs OD). Live: `python scripts/09_observability.py`, then open CloudWatch → GenAI Observability → your agent → Sessions → a trace. |
| 10:45-11:00 | **Break** | | Online evaluation scores Day-2 morning traffic during the break. |
| 11:00-11:15 | 10 Evaluations | theory | Examiner with a marking scheme. Built-in evaluators. Online (continuous) vs spot check (seconds). Judges cost tokens too. |
| 11:15-11:45 | 10 lab | lab | Notebook 10: `agentcore add online-eval` + deploy, spot check, read continuous scores (may be empty until after the break: normal). Live: `python scripts/10_evaluations.py`. |
| 11:45-12:05 | 11 Governance | theory | "Staff only" notice vs a door that needs an ID card. Prompt injection. Cedar: principal/action/resource/when, deny by default, forbid wins, LOG_ONLY vs ENFORCE, automated validation rejecting over-broad policies. |
| 12:05-12:30 | 11 lab (part 1) | lab | Notebook 11: leave Lambda + target, deploy; write the two Cedar policies; `agentcore add policy-engine` (LOG_ONLY) + `add policy` ×2, deploy; LOG_ONLY attacks. Let students try their own injections from `projects/injection_attempts.md`. |
| 12:30-1:15 | **Lunch** | | |
| 1:15-1:30 | 11 lab (part 2) | lab | Switch the mode to ENFORCE in `agentcore.json`, deploy, attack again; "Known limits". Live: `python scripts/11_governance.py`. |
| 1:30-1:45 | Continuous improvement | instructor demo | `python scripts/12_continuous_improvement.py` (see below). Story: observe → evaluate → recommend → A/B test → ship. |
| 1:45-2:45 | 12 Capstone | lab | 5-min brief (5 ideas + rubric), 45-min build, 10-min demos (3-4 volunteers show allowed case, denied case, trace). |
| 2:45-3:00 | Day 2 quiz + feedback | quiz | `assessment/day2-quiz.md`, `assessment/feedback-form.md`. |
| 3:00-3:15 | **Cleanup together** | lab | Everyone runs `bash cleanup/cleanup.sh <their-id>` (Git Bash on Windows) and shows the final `PASS` line. Explain why: cost, security, good habit. |
| 3:15-3:30 | Close | talk | Skills recap, take-home guide (`notebooks/13-take-home-extensions.md`), certificates (`assessment/certificate-text.md`), Q&A. |

---

## Continuous improvement demo (instructor only, "Lab 9")

`python scripts/12_continuous_improvement.py`

1. **Recommendations (real API call, preview in Nov 2026).** AgentCore reads your agent's traces and the `Builtin.Helpfulness` evaluator
   and proposes a better system prompt. Say: "The platform read yesterday's chats and suggests how to rewrite the instructions."
   Show the before/after prompt. Don't apply it blindly: "a suggestion is a hypothesis, not a fix."
2. **Gateway A/B testing (narrated).** The script prints the steps: put two agent versions behind the Gateway (or two versions of a
   configuration bundle), create one online evaluation per variant, `create-ab-test` with a 90/10 split, read per-variant scores with confidence
   intervals, then ship the winner. Analogy: two sections get different worksheet versions and you compare marks before changing it for the batch.
   We don't run it live because it needs a second Runtime variant (more cost and 10+ minutes of setup).

If `start_recommendation` fails (preview not enabled for the account, or not enough traffic yet), narrate from the printed steps and show
the evaluation scores from notebook 10 instead.

---

## What can go wrong, and the fallback

| Problem | Symptom | Fallback |
|---|---|---|
| Bedrock throttling with 40 people | `ThrottlingException`, slow answers | Wait 30 s and retry. Stagger: half the room starts the lab 2 minutes later. |
| `agentcore deploy` slow or failing for one student | Deploy > 6 min or an error | Read the error the cell printed (the CLI explains it). Meanwhile they continue with **your pre-deployed agent**: set `CAMPUSMATE_AGENT_ARN` for the web app in notebook 08. |
| Slow Wi-Fi | `agentcore create` (npm install) or `uv add` crawls | Have students run notebook 05 Steps 1-3 at home as pre-work, or use a hotspot. |
| Memory extraction slow | Notebook 06 polling never finds facts | It's asynchronous; move on to 07 and come back. Show `scripts/06_agentcore_memory.py` on your instance. |
| No spans in CloudWatch | Notebook 09 finds nothing | First-ever spans in an account can take ~10 min. Show your traces from yesterday's traffic in the console. |
| Online evaluation results empty | Notebook 10 shows 0 records | Scoring runs after sessions idle (5 min) plus processing; use the **spot check** cell (on-demand Evaluate API), which answers in seconds. |
| A student can't use bash (Windows) | `bash: command not found` | Git Bash (bundled with Git for Windows). Or WSL. |
| `AccessDeniedException` | The student isn't in the admin group yet | Add their user to the workshop group (takes effect in seconds). |
| Cedar policy fails at deploy in the capstone | *unable to find an applicable action* or *Overly Restrictive* | Deploy the tool first, then add the policy; use `--validation-mode ignore-all-findings` for `forbid` rules. |
| Everything is on fire | | Every Checkpoint names the cell (or `projects/` file) to copy. A student can always re-run a notebook from the top: every step reuses what already exists. |

## After the workshop

- Ask students to run `bash cleanup/cleanup.sh <their-id>` (or run it for them: `bash cleanup/cleanup.sh <id> --yes` for each ID).
- List anything left in the account: `aws resourcegroupstaggingapi get-resources --tag-filters Key=project,Values=campusmate-workshop`.
- Check Cost Explorer two days later (filter by tag `project = campusmate-workshop`, after activating the tag in Billing).
