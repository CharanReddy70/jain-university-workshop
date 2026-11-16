# 13 · Take-home extensions

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

Two short guides to try after the workshop, in your own time. They reuse what you built. **Status: not verified end-to-end by the
workshop author** (see `TEST_REPORT.md`); the API calls follow the AWS documentation as of November 2026. Budget: under US$1 each if you clean up.

---

## A. Lab 8 (bonus): a zero-code agent with AgentCore Harness

**What:** AgentCore **Harness** is a *managed agent loop*. Instead of writing Strands code and deploying it to Runtime, you give AgentCore a
configuration (model, system prompt, tools, memory) and it runs the loop for you. 🏫 Like ordering the canteen's fixed thali instead of cooking.

**When to use which:** Harness for quick, standard agents; Runtime (what you built) when you need your own code, custom tools or a framework.

**Steps (AWS CLI + boto3):**
1. Create an execution role the Harness can assume (trust `bedrock-agentcore.amazonaws.com`, allow `bedrock:InvokeModel` on Amazon Nova), named
   `campusmate-harness-role-<STUDENT_ID>` and tagged `project=campusmate-workshop`.
2. Create the harness. Set limits explicitly:
   ```bash
   aws bedrock-agentcore-control create-harness \
     --harness-name campusmate_harness_<STUDENT_ID> \
     --execution-role-arn arn:aws:iam::<ACCOUNT_ID>:role/campusmate-harness-role-<STUDENT_ID> \
     --max-iterations 10 --max-tokens 2000 --timeout-seconds 120 \
     --tags project=campusmate-workshop,student=<STUDENT_ID>
   ```
   Run `aws bedrock-agentcore-control create-harness help` to see how to set the model, the system prompt and tools (for example your
   Gateway, so the harness can call `check_attendance_eligibility` with **zero** agent code).
3. Wait until `aws bedrock-agentcore-control get-harness --harness-id <id>` says `READY`.
4. Invoke it (the session ID needs 33+ characters, and the answer comes back as a **stream**):
   ```python
   import boto3, uuid
   c = boto3.client("bedrock-agentcore", region_name="us-east-1")
   r = c.invoke_harness(harnessArn="<harness-arn>", runtimeSessionId=f"harness-{uuid.uuid4()}",
                        messages=[{"role": "user", "content": [{"text": "What is the attendance rule at a typical Indian university?"}]}])
   for ev in r["stream"]:
       print(ev.get("contentBlockDelta", {}).get("delta", {}).get("text", ""), end="")
   ```
5. Compare with your Runtime agent: what did you lose (custom local tools, your own memory logic) and what did you gain (no code, no zip)?
6. **Clean up:** `aws bedrock-agentcore-control delete-harness --harness-id <id>` and delete the role.

The AgentCore CLI (`npm install -g @aws/agentcore`, Node.js 20+) can do steps 2-4 with `agentcore create`, `agentcore deploy` and `agentcore invoke`.

---

## B. Lab 10 (bonus): web search through your Gateway

**What:** give CampusMate fresh information from the web (for example, "When is the next AWS Community Day in Bengaluru?") as one more
Gateway tool, under the same AWS_IAM auth and Cedar policy engine as your other tools.

> **Note on Exa:** the original workshop plan said "web search with Exa, us-east-1 only". As of November 2026 the AWS docs describe a
> **managed Web Search tool on AgentCore** (built on Amazon's own search infrastructure, a built-in Gateway connector with `connectorId: "web-search"`),
> available in us-east-1 and, since October 2026, also us-east-2, us-west-2, ap-southeast-2 and GovCloud (US-West). Price: US$7 per 1,000 queries.
> Option B1 uses it. If you specifically want **Exa**, option B2 shows the general pattern for adding an external MCP server; check Exa's own docs.

### B1. Managed Web Search connector (recommended)
1. Allow your gateway role to call it (add to `campusmate-gateway-role-<id>`):
   `{"Effect": "Allow", "Action": "bedrock-agentcore:InvokeWebSearch", "Resource": "arn:aws:bedrock-agentcore:us-east-1:aws:tool/web-search.v1"}`
   (check the exact resource ARN in the Web Search tool documentation).
2. Add the target:
   ```python
   import boto3, sys; sys.path.insert(0, "projects"); import config
   ctl = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
   ctl.create_gateway_target(
       gatewayIdentifier=config.get_resource("gateway_id"), name="websearch",
       targetConfiguration={"mcp": {"connector": {"source": {"connectorId": "web-search"},
                                                  "configurations": [{"name": "WebSearch", "parameterValues": {}}]}}},
       credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}])
   ```
3. Your gateway is in **ENFORCE** mode, and the baseline policy permits all actions on your gateway for your agent and you, so the new
   tool works straight away. Optional: add a Cedar `forbid` on the web-search action (find its exact name with `tools/list`).
4. Ask the deployed agent a current-events question in a **new session** and look for the web-search tool in `tools_used` and in the trace.
5. **Clean up:** delete the `websearch` target (or run `bash cleanup/cleanup.sh`, which deletes all targets on your gateway).

### B2. External MCP server, for example Exa (not verified)
1. Get an API key from the provider. **Never** put it in code or `.env` committed to git.
2. Store it with AgentCore Identity: `aws bedrock-agentcore-control create-api-key-credential-provider --name campusmate-exa-<id> --api-key "$EXA_API_KEY"`.
3. Add an `mcpServer` target pointing at the provider's MCP endpoint, with `credentialProviderType: "API_KEY"` and the provider ARN from step 2
   (see the target skeleton: `aws bedrock-agentcore-control create-gateway-target --generate-cli-skeleton input`).
4. Test with `tools/list` (as in notebook 07), then from the agent in a new session.
5. **Clean up:** delete the target and the credential provider.
