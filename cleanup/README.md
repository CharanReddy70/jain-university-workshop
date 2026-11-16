# Cleanup

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

```bash
bash cleanup/cleanup.sh priya07          # your student ID; asks you to type it again to confirm
bash cleanup/cleanup.sh priya07 --yes    # no prompt
bash cleanup/cleanup.sh                  # instructor: uses STUDENT_ID from .env
```
On Windows, run it from **Git Bash**. It uses the venv's Python automatically.

## Why cleanup matters

- **Cost.** Most of what we built is pay-per-use, but stored memories, log groups, the S3 code bundle and idle resources still cost a little,
  every day, until someone deletes them. 40 students × "a little" × 30 days adds up. Leaving the room without cleaning up is like leaving the
  lab with every PC and AC switched on.
- **Security.** An agent nobody watches, with permissions to call tools, is a liability. Fewer resources = fewer things to attack.
- **Habit.** In a job you'll create and delete environments every week. Engineers who clean up after themselves are the ones who get trusted
  with production.

## What it deletes, in order

Order matters: you can't delete a gateway that still has targets, or a role that a running agent is using.

0. Your AgentCore CLI project from notebooks 05-12: the CloudFormation stack `AgentCore-campusmate<id>-default`
   (runtime, memory, gateway, policies, evaluation and the roles the CLI made). Can take several minutes.
1. Online evaluation config (`campusmate_eval_<id>`, reference system)
2. AgentCore Runtime (`campusmate_<id>`) and waits until it's gone
3. Gateway targets, then the Gateway (`campusmate-gw-<id>`)
4. Cedar policies, then the policy engine (`campusmate_pe_<id>`)
5. AgentCore Memory (`campusmate_mem_<id>`), including all stored events and long-term records
6. Lambda functions (`campusmate-attendance-<id>`, `campusmate-leave-<id>`, and `campusmate-capstone-<id>` if you did the capstone) and their role
7. The S3 code bucket (`campusmate-<id>-<account>-<region>`): every object, then the bucket
8. IAM roles (`campusmate-runtime-role-<id>`, `-gateway-role-`, `-lambda-role-`, `-eval-role-`): inline policies first
9. CloudWatch log groups for the runtime, the Lambdas and the evaluation results
10. `projects/.deployed-resources.json`

It looks every resource up by its per-student name (and also reads `projects/.deployed-resources.json` if `deploy.sh` created one), so it still works after a half-finished
deploy or if the file was deleted. "Already gone" is fine. It never touches resources that don't carry your `STUDENT_ID`.

## Verification

At the end it lists anything still tagged `project=campusmate-workshop` and `student=<id>` (Resource Groups Tagging API), any IAM roles
left, and any Runtime/Gateway/Memory still listed by name, then prints:

```
PASS: nothing for this STUDENT_ID remains. Thanks for cleaning up!
```
The tagging index can lag a few minutes behind deletions; the script double-checks by name and tells you if that's all it is.

## Redeploying right after cleanup

AgentCore Memory deletion runs in the background and can take **10-30 minutes** when it holds many records. Until it finishes, the memory
*name* stays reserved. `deploy.sh` detects this and waits ("an earlier memory with this name is still being deleted"), so you can just leave it running.

## Not covered

- Your local project folder `campusmate<id>/` (delete it yourself if you like; it's git-ignored).

- The account-level **CloudWatch Transaction Search** setting (shared by everyone; harmless to leave on; costs nothing below 1% indexing).
- Anything you created by hand in the console with other names. Search the console for `campusmate` if in doubt.
