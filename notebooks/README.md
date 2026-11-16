# Notebooks: the student labs

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

Twelve labs that build **CampusMate** step by step, from a raw model call to a governed, observable, evaluated agent on AWS.
Each notebook has the same shape, so you always know where you are:

1. **Title and time budget** (theory minutes + hands-on minutes)
2. **Why this matters** and what you'll do
3. **Theory** in short cells, with a campus analogy
4. **🔬 Live check**: a cell that proves it works
5. **✍️ Your turn**: an exercise with `# TODO` stubs (the cell runs safely before you fill it in)
6. **✅ Checkpoint**: expected output, and which `projects/` file to copy if you fall behind
7. **🛠️ Common errors** with the exact fix

## Start

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
jupyter notebook notebooks/
```
Run cells top to bottom with **Shift+Enter**. If something is weird, *Kernel → Restart* and run from the top.

## Learning path

| # | Notebook | Time | CampusMate | Key idea |
|---|---|---|---|---|
| 01 | genai-foundations | 25 + 15 | v0 | Tokens, context, temperature, hallucination, statelessness, thinking |
| 02 | aws-essentials | 10 + 20 | v0 | Account, IAM, region, CLI, reading an AccessDenied |
| 03 | first-strands-agent | 15 + 30 | v0 | A 4-line agent, then one idea at a time: personality, conversation, model, cost, first tool |
| 04 | strands-agents-and-tools | 20 + 60 | v1 | Agent loop, `@tool`, local tools over `data/` |
| 05 | agentcore-runtime | 15 + 30 | v2 | Your notebook-04 agent + 3-line wrapper; `agentcore create` / `deploy` / `invoke`; sessions |
| 06 | agentcore-memory | 15 + 30 | v3 | `agentcore add memory`; short vs long-term; extraction runs in the background |
| 07 | gateway-lambda-tools | 15 + 30 | v4 | MCP; a Lambda tool behind `agentcore add gateway` |
| 08 | customer-interface | 10 + 35 | v5 | Flask portal; actor ID and session ID |
| 09 | observability | 15 + 30 | v6 | Traces, spans, token cost; the bad-answer recipe |
| 10 | evaluations | 15 + 30 | v7 | LLM-as-a-judge: online vs spot check |
| 11 | governance-cedar-policies | 20 + 40 | v8 | Prompt injection vs Cedar policy at the Gateway |
| 12 | capstone | 60 | yours | Your own tool + your own policy + the trace |
| 13 | take-home-extensions.md | | | Harness (zero-code agents), web search via Gateway |

## How notebooks, scripts and projects fit together

- `notebooks/NN-*.ipynb`: **you** run these (the lab).
- `scripts/NN_*.py`: the instructor's short live demo for the same module.
- **Your AgentCore project**: notebook 05 creates a folder `campusmate<your id>` next to `notebooks/` with the AgentCore CLI. Your agent
  lives in `campusmate<your id>/app/agent/main.py`; notebooks 06-12 add memory, a gateway, evaluation and policies to the same project.
- `projects/`: the finished reference system. Behind? Each Checkpoint names the cell (or file) to copy.

## Rules of the road

- In each notebook's **Settings** cell, change `STUDENT_ID = "student01"` to your own ID (the same in every notebook). Every AWS resource you create carries it.
- Later notebooks find what you built earlier by its name, so there are no IDs to copy between notebooks.
- Don't paste AWS keys into notebooks. `aws configure` keeps them outside the repo.
- At the end of Day 2: `bash cleanup/cleanup.sh <your-student-id>`.
