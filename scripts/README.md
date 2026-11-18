# Instructor guide: run-of-show, live demos and fallbacks

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

Each `scripts/NN_*.py` is a 10-25 line live demo for the module with the same number as `notebooks/NN-*.ipynb`. Run them from the
**repo root** with the venv active: `python scripts/04_strands_tools.py`. Type them live if you like; they are short on purpose.
Settings are plain variables at the top of each script.

| Script | What it shows | Needs deployed system? |
|---|---|---|
| `check_setup.py` | One-command pre-flight: Python, packages, identity, region, model access, AgentCore | no |
| `01_genai_demos.py` | Hallucinated "Rule 42B", statelessness, temperature 0 vs 1 | no |
| `02_aws_identity_check.py` | Who am I, region, a deliberate `AccessDenied` and how to read it | no |
| `03_first_agent.py` | A 3-line agent, then a personality + remembered chat, then a first tool | no |
| `04_strands_tools.py` | Strands agent with two `@tool`s over `data/*.json` | no |
| `mcp.json` | Example MCP client config (from the original workshop) for local MCP servers | no |

---

## Pre-workshop checklist (do it 2-3 days before)

- [ ] **Account**: a sandbox AWS account just for the workshop; billing alerts set (AWS Budgets, for example US$300 with email alerts at 50/80/100%).
- [ ] **Region**: `us-east-1`. Confirm AgentCore is there: `aws bedrock-agentcore-control list-agent-runtimes --region us-east-1`.
- [ ] **Model access**: `python scripts/check_setup.py` passes as the instructor (it calls both models).
- [ ] **Quotas** (Service Quotas console → Amazon Bedrock): requests/tokens per minute for the Amazon Nova 2 Lite cross-region profile.
  40 students × ~3 calls per question can spike to ~100 requests/minute during labs. Request an increase a week ahead if the default is lower.
  AgentCore defaults (runtimes, gateways, memories per account) are well above 40 each, but check *Amazon Bedrock AgentCore* in Service Quotas.
- [ ] **Student access**: one IAM user per student in an IAM group with the AWS-managed `AdministratorAccess` policy (see SETUP.md), access keys handed out privately. Use a separate sandbox account.
- [ ] **CDK bootstrap** (the AgentCore CLI deploys through AWS CDK): `cdk bootstrap aws://<ACCOUNT_ID>/us-east-1` once, or check the `CDKToolkit` stack exists. If the account is in an AWS Organization, check no SCP blocks `bedrock-agentcore:*`, CloudFormation or cross-region inference.
- [ ] **Laptop tools**: Python 3.10+, AWS CLI, **Node.js 20+, the AgentCore CLI (`npm install -g @aws/agentcore`) and uv**. `check_setup.py` checks all of them.
- [ ] **Rehearse**: run notebooks 01-07 once with a test `STUDENT_ID`, including the cleanup cell at the end of 07.
- [ ] **Send SETUP.md** to students 3 days ahead; ask for a screenshot of `check_setup.py` passing.
- [ ] **Wi-Fi**: test that `pip install` and `*.amazonaws.com` work on the lab network; have a hotspot as plan B.

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
| 9:00-9:05 | Welcome | talk | Who we are, what CampusMate is. Show what we'll build: CampusMate answering from real campus rules. |
| 9:05-9:25 | 01 GenAI foundations | theory | LLM = predicts next text (the senior who read every notice board). Tokens = what you pay for. Context window = answer-sheet size. Temperature. Hallucination. Statelessness. Thinking tokens (new in 2026). |
| 9:25-9:40 | 01 demos | demo | `python scripts/01_genai_demos.py`. Pause after Rule 42B: "Did it make it up or refuse? Either way, would you trust it with exam rules?" Then statelessness: "This is why chat apps resend everything." |
| 9:40-9:50 | 02 AWS essentials | theory | Account = college, IAM = ID cards, policy = which rooms your card opens, region = which campus. Why us-east-1. |
| 9:50-10:10 | 02 lab + Bedrock | lab | Students run notebook 02 (who am I, setup check). Then a live look at Amazon Bedrock in the console, before agents. |
| 10:10-10:25 | 03 Your first Strands agent | theory | What an agent is: model + instructions + tools. Strands = the admission portal that talks to every office (Bedrock) for you. One model (Nova 2 Lite), tokens = money. |
| 10:25-10:45 | 03 lab (part 1) | lab | Notebook 03 Steps 1-4: type the 4-line agent together first, then personality, conversation, model choice. Live: `python scripts/03_first_agent.py`. |
| 10:45-11:00 | **Break** | | |
| 11:00-11:10 | 03 lab (part 2) | lab | Step 5 (cost) and Step 6 (first tool) + "Your turn". Ask one student to explain the 4-step tool loop in their own words. |
| 11:10-11:30 | 04 Strands tools | theory | Agent loop (reason, act, observe). `@tool` docstrings are advertisements to the model. From a toy tool to real ones that read the course list and rulebook. |
| 11:30-12:30 | 04 lab | lab | Notebook 04: build both tools, test in a loop, "Your turn" `get_event_info`. Live: `python scripts/04_strands_tools.py`. Walk the room. |
| 12:30-1:15 | **Lunch** | | Kick off nothing heavy; quotas reset per minute anyway. |
| 1:15-1:30 | 05 Memory | theory | Attendance register (short-term) vs department file (long-term). Semantic vs summary. Actor = student, session = one conversation. **Extraction is asynchronous**: say it twice. |
| 1:30-2:30 | 05 lab | lab | Notebook 05: create the Memory (2-3 min, explain while it runs), CampusMate with `session_manager=`, tell a fact, wait for extraction, a new conversation remembers. |
| 2:30-3:30 | Wrap-up | talk | "Today: brain, tools, memory. Tomorrow: a report card (LLM-as-a-judge), then we deploy to AgentCore Runtime and clean up." |

## Day 2: grade it, deploy it, clean up (9:00 AM - 1:00 PM)

| Time | Block | Type | What to do and say |
|---|---|---|---|
| 9:00-9:10 | Recap | talk | Recap Day 1 (model, tools, memory). |
| 9:10-9:25 | 06 LLM-as-a-judge | theory | Examiner with a marking scheme: student = CampusMate, answer key = campus data, examiner = a second model. Always give a key; temperature 0. |
| 9:25-10:15 | 06 lab | lab | Notebook 06: build the judge, warm-up (good vs bad answer), the 5-question exam from `data/`, report card, "Your turn" question. Runs on the laptop, no deploy needed. |
| 10:15-10:30 | **Break** | | |
| 10:30-10:45 | 07 Runtime | theory | Prototype-to-production gap (cooking at home vs running the canteen). microVM per session, 33-char session IDs, the 3-line wrapper. |
| 10:45-12:00 | 07 lab | lab | Notebook 07: `agentcore create` → write the agent (tools + memory + wrapper) → libraries into `pyproject.toml` (check the ✅ line) → `agentcore add memory` → `agentcore deploy` (3-5 min) → invoke: same vs new session, memory in the cloud. |
| 12:00-12:20 | **Cleanup together** | lab | Everyone runs the last cell of notebook 07 (`CONFIRM = True`) and shows the `PASS` line. Same on macOS and Windows. Explain why: cost, security, good habit. |
| 12:20-1:00 | Close | talk | Skills recap (model, tools, memory, judge, Runtime), Q&A. |

---


## What can go wrong, and the fallback

| Problem | Symptom | Fallback |
|---|---|---|
| Bedrock throttling with 40 people | `ThrottlingException`, slow answers | Wait 30 s and retry. Stagger: half the room starts the lab 2 minutes later. |
| `agentcore deploy` slow or failing for one student | Deploy > 6 min or an error | Read the error the cell printed (the CLI explains it). Most often: Step 3 wasn't run before deploy. Run Step 3 again (look for ✅ strands-agents), then deploy again. |
| Slow Wi-Fi | `agentcore create` (npm install) crawls | Have students run notebook 07 Steps 1-3 early, or use a hotspot. |
| Memory extraction slow | Notebook 05 polling never finds facts | It's asynchronous; run the Step 4 cell again after a minute, or move on and come back. |
| A student can't use bash (Windows) | `bash: command not found` | Git Bash (bundled with Git for Windows). Or WSL. |
| `AccessDeniedException` | The student isn't in the admin group yet | Add their user to the workshop group (takes effect in seconds). |
| Everything is on fire | | Every Checkpoint says what to do if you fall behind. A student can always re-run a notebook from the top: every step reuses what already exists. |

## After the workshop

- Ask students to run the last cell of notebook 07 with `CONFIRM = True`. Then check CloudFormation for any `AgentCore-campusmate*` stacks left.
- List anything left in the account: `aws resourcegroupstaggingapi get-resources --tag-filters Key=project,Values=campusmate-workshop`.
- Check Cost Explorer two days later (filter by tag `project = campusmate-workshop`, after activating the tag in Billing).
