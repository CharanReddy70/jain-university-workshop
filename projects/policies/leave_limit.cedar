// leave_limit.cedar - CampusMate governance rule (Lab 11)
//
// Deny any leave request longer than 3 days, no matter what the agent was told.
// `forbid` always beats `permit` in Cedar, so this holds even though a separate
// baseline policy permits the CampusMate tools on this gateway.
//
// The gateway uses AWS_IAM inbound auth, so every caller is an AgentCore::IamEntity.
// {{GATEWAY_ARN}} is replaced with your gateway ARN by deploy.sh / notebook 11.
// The action name is "<gateway target name>___<tool name>".
forbid(
  principal is AgentCore::IamEntity,
  action == AgentCore::Action::"leave___submit_leave_request",
  resource == AgentCore::Gateway::"{{GATEWAY_ARN}}"
)
when {
  context.input.days > 3
};
