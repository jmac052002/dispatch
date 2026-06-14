import hashlib
import hmac
import json
import logging
import os

import boto3
from fastapi import FastAPI, Request, HTTPException, Header
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    raise EnvironmentError(
        "Required environment variable 'WEBHOOK_SECRET' is not set."
    )

_lambda_client = boto3.client(
    "lambda",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)


def validate_signature(payload: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False

    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature_header)


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=None)
):
    payload = await request.body()

    if not validate_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    workflow_run = event.get("workflow_run", {})

    if workflow_run.get("conclusion") == "failure":
        repo = event.get("repository", {}).get("full_name", "unknown")
        workflow = workflow_run.get("name", "unknown")
        run_id = workflow_run.get("id")
        conclusion = workflow_run.get("conclusion")

        _lambda_client.invoke(
            FunctionName=os.getenv("AWS_LAMBDA_FUNCTION_NAME", "dispatch"),
            InvocationType="Event",
            Payload=json.dumps({
                "dispatch_action": "triage",
                "repo": repo,
                "workflow": workflow,
                "run_id": run_id,
                "conclusion": conclusion,
            }).encode(),
        )
        logger.info(
            "Async triage invoked: repo=%s, run_id=%s", repo, run_id
        )

    return {"status": "received"} 