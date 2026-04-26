# Dispatch

AI-powered DevOps incident triage assistant. When a GitHub Actions workflow fails or a CloudWatch alarm fires, Dispatch receives the webhook, invokes Claude with real investigation tools, and produces a structured triage summary posted to Slack, GitHub, or S3.

## Stack
- Anthropic SDK (Claude) LLM reasoning and tool calling
- FastAPI webhook receiver
- AWS Lambda + API Gateway serverless deployment
- Docker + ECR containerized Lambda
- AWS CloudWatch, ECS, EC2 investigation tools
- FastMCP conversational access via Claude Desktop
- Terraform all infrastructure as code

## Phases
1. Tool calling from scratch raw Anthropic SDK loop 
2. Webhook receiver FastAPI + Lambda + signature validation
3. Tool suite CloudWatch, GitHub API, ECS/EC2
4. MCP server FastMCP + Claude Desktop
5. Deploy + IaC Terraform, ECR, Secrets Manager, IAM

## Local Development
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY
python src/tool_loop.py
```

## Security
API keys are stored in AWS Secrets Manager in production. Never commit `.env`.