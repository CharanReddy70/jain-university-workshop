"""
Module 11 live demo: the Cedar policy lives at the Gateway, outside the agent. Call the
leave tool directly (as a tricked agent would): 2 days passes, 5 days is denied.
Run: python scripts/11_governance.py
"""
import asyncio
import boto3
from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client

STUDENT_ID, REGION = "instructor", "us-east-1"
ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
gw = next(g for g in ctl.list_gateways(maxResults=100)["items"] if g["name"] == f"campusmate-gw-{STUDENT_ID}")
GATEWAY_URL = ctl.get_gateway(gatewayIdentifier=gw["gatewayId"])["gatewayUrl"]

async def file_leave(days):
    async with aws_iam_streamablehttp_client(endpoint=GATEWAY_URL, aws_service="bedrock-agentcore", aws_region=REGION) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            try:
                r = await s.call_tool("leave___submit_leave_request", {"student_id": "AIDD-DEMO-001",
                                      "start_date": "2026-12-01", "days": days, "reason": "demo"})
                return ("DENIED " if r.isError else "ALLOWED ") + r.content[0].text[:200]
            except Exception as e:
                return f"DENIED {e}"

for d in (2, 5):
    print(f"{d} days ->", asyncio.run(file_leave(d)))
print("\nPolicy file: projects/policies/leave_limit.cedar")
