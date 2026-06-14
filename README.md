# Dispatch

AI-powered DevOps incident triage assistant. When a GitHub Actions workflow
fails, Dispatch receives the webhook, invokes Claude with real investigation
tools, and delivers a structured triage summary to Slack and S3 automatically.

## How It Works

GitHub Actions failure

↓

API Gateway webhook (signature validated)

↓

Lambda — returns 200 immediately

↓ (async self-invocation)

Lambda — Claude tool loop

├── get_github_workflow_logs  → GitHub API

├── get_cloudwatch_logs       → AWS CloudWatch

└── get_ecs_service_status    → AWS ECS

↓

Triage summary

├── S3 (structured JSON record)

└── Slack (rich block message with View Run button)

## Stack

- **LLM** — Anthropic SDK, Claude tool calling loop
- **Webhook** — FastAPI + Mangum, X-Hub-Signature-256 validation
- **Compute** — AWS Lambda (arm64, containerised), API Gateway HTTP API
- **Storage** — S3 for triage JSON records
- **Notifications** — Slack incoming webhooks
- **Secrets** — AWS Secrets Manager
- **Container** — Docker, ECR
- **IaC** — Terraform (ECR, Lambda, API Gateway, S3, IAM, Secrets Manager)
- **Conversational access** — FastMCP server, Claude Desktop

## Project Structure

src/

├── lambda_handler.py   # Lambda entry point — routes webhook and async triage events

├── webhook.py          # FastAPI app, signature validation, async invoke

├── triage.py           # Claude tool loop — multi-turn with real tool calls

├── tools.py            # CloudWatch, GitHub API, ECS tool implementations

├── output.py           # S3 triage record writer

├── slack_output.py     # Slack block message formatter and poster

└── tool_loop.py        # Phase 1 standalone script (learning reference)
mcp_server/

├── server.py           # FastMCP server exposing tools to Claude Desktop

└── tools/

├── cloudwatch.py

├── github.py

└── ecs.py
terraform/

├── main.tf             # Lambda, API Gateway, S3, Secrets Manager

├── iam.tf              # Execution role, policies, self-invoke permission

├── variables.tf

├── outputs.tf

└── terraform.tfvars    # Not committed — see Environment Variables below

## Phases

1. **Tool calling** — raw Anthropic SDK tool loop, no frameworks
2. **Webhook receiver** — FastAPI + Mangum + X-Hub-Signature-256 validation
3. **Tool suite** — CloudWatch logs, GitHub API, ECS service status
4. **MCP server** — FastMCP wrapping the same tools, Claude Desktop connection
5. **Deploy + IaC** — Terraform, ECR, API Gateway, Secrets Manager, IAM
6. **Production pipeline** — async Lambda self-invocation, Slack output

## Deploying

### Prerequisites

- AWS CLI configured
- Terraform >= 1.6
- Docker
- Python 3.12

### Infrastructure

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars  # fill in your values
terraform init
terraform apply
```

### Build and push the Lambda image

```bash
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin \
    <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker build --platform linux/arm64 --provenance=false -t dispatch .
docker tag dispatch:latest <ecr-repo-url>:latest
docker push <ecr-repo-url>:latest

aws lambda update-function-code \
  --function-name dispatch \
  --image-uri <ecr-repo-url>:latest \
  --region us-east-1
```

### GitHub webhook

In your repo: Settings → Webhooks → Add webhook

- Payload URL: your API Gateway URL from Terraform outputs
- Content type: `application/json`
- Secret: matches `WEBHOOK_SECRET` in Lambda
- Events: `Workflow runs`

## Environment Variables

Lambda reads these from its environment (managed by Terraform):

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `GITHUB_TOKEN` | GitHub personal access token |
| `WEBHOOK_SECRET` | GitHub webhook signing secret |
| `S3_BUCKET` | Triage output bucket name |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL |
| `GITHUB_REPO` | Repository in owner/repo format |
| `AWS_ACCOUNT_ID` | AWS account ID |

For local development, copy `.env.example` to `.env` and fill in values.

## MCP Server (Claude Desktop)

The FastMCP server exposes the same investigation tools to Claude Desktop
for conversational access.

```bash
source .venv/bin/activate
./start_mcp.sh
```

Configure in Claude Desktop via `claude_desktop_config.json`.

## Security

- All secrets stored in AWS Secrets Manager
- Webhook signature validated on every request (HMAC-SHA256)
- Lambda IAM role follows least-privilege
- `.env` excluded from Docker builds via `.dockerignore`
- Never commit `terraform.tfvars` or `.env`