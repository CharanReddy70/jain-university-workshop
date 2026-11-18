# Notebooks: the student labs

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

Seven labs that build **CampusMate** step by step: a model, tools, memory, a report card, and finally a deploy to AgentCore Runtime.
Each notebook has the same shape, so you always know where you are:

1. **Title and time budget** (theory minutes + hands-on minutes)
2. **Why this matters** and what you'll do
3. **Theory** in short cells, with a campus analogy
4. **🔬 Live check**: a cell that proves it works
5. **✍️ Your turn**: an exercise with `# TODO` stubs (the cell runs safely before you fill it in)
6. **✅ Checkpoint**: expected output, and what to do if you fall behind
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
| 02 | aws-essentials | 10 + 20 | v0 | Account, IAM user, region, setup check; then a look at Amazon Bedrock |
| 03 | first-strands-agent | 15 + 30 | v0 | A 4-line agent, then one idea at a time: personality, conversation, model, cost, first tool |
| 04 | strands-agents-and-tools | 20 + 60 | v1 | Agent loop, `@tool`, local tools over `data/` |
| 05 | agentcore-memory | 15 + 30 | v2 | Create an AgentCore Memory; short vs long-term; a new conversation remembers |
| 06 | llm-as-a-judge | 15 + 30 | v3 | A judge model marks CampusMate's answers against the campus data |
| 07 | deploy-to-agentcore-runtime | 15 + 40 | v4 | Tools + memory + 3-line wrapper; `agentcore create` / `add memory` / `deploy` / `invoke`; clean up |

## How notebooks, scripts and projects fit together

- `notebooks/NN-*.ipynb`: **you** run these (the lab).
- `scripts/NN_*.py`: the instructor's short live demo for the same module.
- **Your AgentCore project**: notebook 07 creates a folder `campusmate<your id>` next to `notebooks/` with the AgentCore CLI and deploys it.

## Rules of the road

- In each notebook's **Settings** cell, change `STUDENT_ID = "student01"` to your own ID (the same in every notebook). Every AWS resource you create carries it.
- Later notebooks find what you built earlier by its name, so there are no IDs to copy between notebooks.
- Don't paste AWS keys into notebooks. `aws configure` keeps them outside the repo.
- At the end: run the last cell of `notebooks/07-deploy-to-agentcore-runtime.ipynb` (set `CONFIRM = True`).
