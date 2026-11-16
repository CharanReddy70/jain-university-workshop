# Setup (pre-work): do this BEFORE Day 1

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

⏱️ **About 30 minutes.** Please finish it at home or in the lab the day before. On Day 1 we start coding at 9:00 sharp, and 40 laptops
downloading Python packages on the same Wi-Fi is slow.

You need: a laptop (macOS or Windows 10/11), internet access, and the **AWS access key** your instructor gives you
(an IAM user in the workshop sandbox account). You do **not** need your own AWS account or a credit card.

---

## Step 1: Install Python 3.10 or newer (3.12 recommended)

Strands Agents and the AgentCore SDK need **Python 3.10+** (older guides that say 3.8 are wrong).

**macOS**
```bash
python3 --version                 # if it says 3.10, 3.11, 3.12 or 3.13 you're fine
brew install python@3.12          # if not; needs Homebrew from https://brew.sh
python3.12 --version
```

**Windows**
1. Download Python 3.12 from https://www.python.org/downloads/windows/
2. Run the installer and **tick "Add python.exe to PATH"** on the first screen.
3. Open a new *PowerShell* window: `py -3.12 --version`

## Step 2: Install Git and the AWS CLI v2

- Git: macOS `brew install git` · Windows https://git-scm.com/download/win
- AWS CLI v2: macOS `brew install awscli` · Windows https://awscli.amazonaws.com/AWSCLIV2.msi
- Check: `aws --version` should print `aws-cli/2.x`. Close and reopen the terminal after installing.

## Step 2b: Install Node.js, the AgentCore CLI and uv

From notebook 05 on, we deploy CampusMate with the official **AgentCore CLI** (`agentcore`). It needs **Node.js 20+** and **uv**
(a fast Python package tool).

**macOS**
```bash
brew install node uv
npm install -g @aws/agentcore
agentcore --version        # 1.0 or newer
uv --version
```

**Windows (PowerShell)**
1. Install Node.js **LTS** (20 or newer) from https://nodejs.org and reopen PowerShell.
2. Then:
```powershell
npm install -g @aws/agentcore
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
agentcore --version
uv --version
```
If `agentcore --version` prints an error, an old Python tool with the same name may be in the way: `pip uninstall bedrock-agentcore-starter-toolkit`, then open a new terminal.

## Step 3: Get the workshop code and create a virtual environment

A **virtual environment (venv)** is a private folder of Python packages for this project, so nothing clashes with other projects.

**macOS**
```bash
git clone <repo-url-from-instructor> campusmate-workshop
cd campusmate-workshop
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
git clone <repo-url-from-instructor> campusmate-workshop
cd campusmate-workshop
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If PowerShell says *running scripts is disabled*, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.

You'll see `(.venv)` at the start of your prompt when the venv is active. **Activate it every time you open a new terminal.**

## Step 4: Configure AWS credentials

```bash
aws configure
#   AWS Access Key ID:     <from your instructor>
#   AWS Secret Access Key: <from your instructor>
#   Default region name:   us-east-1
#   Default output format: json
aws sts get-caller-identity       # shows the account and your user name
aws configure get region          # us-east-1
```
Your keys are stored in `~/.aws/credentials`, **outside** the project. Never paste keys into `.env`, notebooks, screenshots or WhatsApp.

## Step 5: Bedrock model access

Amazon Bedrock now enables serverless foundation models by default, so there is usually nothing to do. The check script in Step 7
makes one tiny call to each model we use. If it fails with `AccessDeniedException ... model access`, tell your instructor
(they enable it once for the whole account in the Bedrock console → **Model access**).

## Step 6: Choose your student ID

Pick a unique ID, for example your roll number or first name plus two digits (`priya07`): lower-case letters and digits only,
max 16 characters. Write it down. In every lab notebook, the first code cell (**Settings**) has a line

```python
STUDENT_ID = "student01"
```
Change it to your ID before running anything else. **Every AWS resource you create gets this ID in its name**, so 40+ students
can share one account without clashing. Use the same ID in `projects/web/app.py` (Lab 8) and when you clean up at the end
(`bash cleanup/cleanup.sh priya07`).

## Step 7: Run the setup check

```bash
python scripts/check_setup.py
```
Every line should say `PASS` and it should end with **All checks passed. You are ready for Day 1!**
Each `FAIL` line comes with a `FIX:` line telling you what to do.

Optional: `jupyter notebook notebooks/` and open `01-genai-foundations.ipynb` to make sure Jupyter starts.

---

## AWS permissions (instructor)

To keep the workshop smooth, give every student IAM user **administrator access** in the workshop sandbox account: create an IAM group
(for example `campusmate-students`), attach the AWS-managed policy **`AdministratorAccess`**, and add the student users to it.

Before Day 1, as the instructor, run once in the account and region:
- `cdk bootstrap aws://<ACCOUNT_ID>/us-east-1` (the AgentCore CLI deploys through AWS CDK; skip if the `CDKToolkit` stack already exists)
- `python scripts/check_setup.py`

> Use a **separate sandbox account** for the workshop, set a budget alert, and remove the student users (or the group's policy) after the
> workshop. Every student resource is named with their `STUDENT_ID`, so `bash cleanup/cleanup.sh <id>` removes exactly their things.

---

## Troubleshooting

| You see | What it means | Fix |
|---|---|---|
| `python3: command not found` / `'python' is not recognized` | Python not installed or not on PATH | macOS: `brew install python@3.12`. Windows: reinstall with **Add python.exe to PATH**, open a new terminal |
| `ERROR: Package 'strands-agents' requires a different Python: 3.9.6 not in '>=3.10'` | venv built with an old Python | Delete `.venv`, recreate with `python3.12 -m venv .venv` (Windows `py -3.12 -m venv .venv`) |
| `ModuleNotFoundError: No module named 'strands_agents'` | Old tutorial import | Use `from strands import Agent` |
| `ModuleNotFoundError: No module named 'strands'` | venv not active, or install skipped | Activate the venv, then `pip install -r requirements.txt` |
| `Unable to locate credentials. You can configure credentials by running "aws configure".` | No AWS keys | `aws configure` with the keys from your instructor |
| `An error occurred (InvalidClientTokenId) when calling the GetCallerIdentity operation: The security token included in the request is invalid.` | Key ID mistyped or deleted | Re-run `aws configure`; ask for new keys if it persists |
| `An error occurred (ExpiredToken)` | Temporary credentials expired | Log in again / refresh keys |
| `AccessDeniedException: User: arn:aws:iam::...:user/xyz is not authorized to perform: ...` | Your user isn't in the admin group yet | Ask the instructor to add you to the workshop group |
| `ValidationException: Invocation of model ID amazon.nova-2-lite-v1:0 with on-demand throughput isn't supported` | Used a bare model ID | Use the inference profile from `projects/config.py` (`us.amazon.nova-2-lite-v1:0`) |
| `AccessDeniedException ... model access` for Nova | Amazon Nova 2 Lite isn't enabled in the account | Bedrock console → **Model access** → enable Amazon Nova 2 Lite |
| `MaxTokensReachedException` or an empty answer with `stopReason: max_tokens` | The model spent the token budget thinking | Raise `MAX_TOKENS` in `.env` (default 1200) or `maxTokens` in the call |
| `ThrottlingException: Too many requests` | 40 people sharing one account's quota | Wait 30 s and retry |
| `ValidationException ... runtimeSessionId ... length` | Runtime session IDs need 33+ characters | Use `f"lab-{uuid.uuid4()}"` |
| `Tool Execution Denied: Tool call not allowed due to policy enforcement` | The Cedar policy blocked the call | Expected for leave above 3 days. Otherwise check your policies are ACTIVE |
| `OSError: [Errno 48] Address already in use` (port 5000/5050/8080) | Another app uses the port (AirPlay uses 5000 on Macs) | `PORT=8000 python projects/web/app.py` |
| PowerShell: `running scripts is disabled on this system` | Execution policy blocks venv activation | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `bash: command not found` on Windows | No bash in PowerShell | Use **Git Bash** (comes with Git for Windows) for `cleanup.sh` |
| `'agentcore' is not recognized` / `command not found: agentcore` | AgentCore CLI not installed or terminal not reopened | `npm install -g @aws/agentcore`, then open a new terminal and restart Jupyter |
| `agentcore deploy` fails mentioning CDK or bootstrap | The account isn't CDK-bootstrapped | Instructor runs `cdk bootstrap aws://<ACCOUNT_ID>/us-east-1` once |
| `SSL: CERTIFICATE_VERIFY_FAILED` on campus Wi-Fi | Network proxy intercepts HTTPS | Use a mobile hotspot, or ask IT for the proxy CA certificate |
