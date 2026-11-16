"""
Module 02 live demo: who am I, where am I, and what a permission error looks like.
Run: python scripts/02_aws_identity_check.py
"""
import json, sys
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
me = boto3.client("sts").get_caller_identity()
print(f"Account: {me['Account']}\nIdentity: {me['Arn']}\nRegion: {REGION}")

# A deliberately tiny "visitor pass": only allowed to ask "who am I?"
only_whoami = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "sts:GetCallerIdentity", "Resource": "*"}]}
try:
    creds = boto3.client("sts").get_federation_token(Name="campusmate-demo", Policy=json.dumps(only_whoami), DurationSeconds=900)["Credentials"]
except ClientError as e:
    sys.exit(f"(Skipping the permission demo: {e.response['Error']['Code']} - needs IAM-user keys and sts:GetFederationToken)")
visitor = boto3.Session(aws_access_key_id=creds["AccessKeyId"], aws_secret_access_key=creds["SecretAccessKey"],
                        aws_session_token=creds["SessionToken"], region_name=REGION)
try:
    visitor.client("bedrock").list_foundation_models()
except ClientError as e:
    print("\nDELIBERATE ERROR ->", e.response["Error"]["Code"], ":", e.response["Error"]["Message"][:160])
    print("Read it like an exam-cell notice: WHO (the user), tried WHAT (bedrock:ListFoundationModels), was NOT ALLOWED.")
    print("FIX: add that action to the policy. With your normal identity it works:")
print(len(boto3.client("bedrock", region_name=REGION).list_foundation_models()["modelSummaries"]), "models visible")
