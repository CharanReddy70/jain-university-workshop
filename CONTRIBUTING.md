# Contributing

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

Thanks for improving the workshop! A few rules keep it reliable for 40+ students at once.

- **Keep the structure.** `notebooks/NN-*.ipynb` (student lab) pairs with `scripts/NN_*.py` (10-25 line live demo); `projects/` is the reference system.
- **Plain settings for students.** Notebooks, the agent, the web app and the demo scripts keep their settings (region, model IDs, `STUDENT_ID`) as plain variables at the top: no config modules or hidden files. `projects/config.py` is only for the instructor tools. When a model ID changes, search and replace it everywhere.
- **Verify against current docs.** AgentCore, Strands and Cedar APIs change quickly. Check the official docs and `pip show`/introspection, then record
  any behaviour change in `TEST_REPORT.md`.
- **Fictional data only.** Everything in `data/` starts with a `_note` and must not describe real people, real rules or real contact details.
- **Idempotent and per-student.** Every AWS resource name includes `STUDENT_ID` (the CLI project is `campusmate<id>`), and
  `cleanup/cleanup.sh <id>` must remove it.
- **Keep IAM out of the labs.** Students run with admin access in a sandbox account; the AgentCore CLI creates the service roles. Don't add IAM policy steps to notebooks.
- **No secrets.** Never commit `.env`, keys or account-specific ARNs.
- **Test before a PR:** `python scripts/check_setup.py`, run the notebooks you touched (`jupyter nbconvert --to notebook --execute ... --output-dir notebooks/build`),
  `bash projects/deploy.sh && bash scripts/smoke_test.sh`, then `bash cleanup/cleanup.sh --yes`.
- Notebooks are committed **without outputs**. Clear them before committing.
