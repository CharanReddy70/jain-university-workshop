"""
Module 07 live demo: AgentCore Gateway is an MCP server. List its tools and call the
Lambda-backed attendance tool directly, signed with our AWS identity (AWS_IAM auth).
Run: python scripts/07_gateway_lambda.py
"""
import asyncio
import boto3
from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client

STUDENT_ID, REGION = "instructor", "us-east-1"
ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
gw = next(g for g in ctl.list_gateways(maxResults=100)["items"] if g["name"] == f"campusmate-gw-{STUDENT_ID}")
GATEWAY_URL = ctl.get_gateway(gatewayIdentifier=gw["gatewayId"])["gatewayUrl"]

async def main():
    async with aws_iam_streamablehttp_client(endpoint=GATEWAY_URL, aws_service="bedrock-agentcore", aws_region=REGION) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            print("Tools:", [t.name for t in (await s.list_tools()).tools])
            for sid in ("AIDD-DEMO-003", "AIDD-DEMO-004"):
                r = await s.call_tool("attendance___check_attendance_eligibility", {"student_id": sid})
                print(f"\n{sid}:", r.content[0].text[:300])

asyncio.run(main())
