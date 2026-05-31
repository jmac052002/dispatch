import hashlib
import hmac
import logging
import os

from fastapi import FastAPI, Request, HTTPException, Header
from mangum import Mangum
from dotenv import load_dotenv
from triage import run_triage
from output import save_to_s3

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    raise EnvironmentError(
        "Required environment variable 'WEBHOOK_SECRET' is not set."
    )


def validate_signature(payload: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False

    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    expected_header = f"sha256={expected}"
    return hmac.compare_digest(expected_header, signature_header)


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

        logger.info(
            "Triage triggered: repo=%s, workflow=%s, run_id=%s",
            repo, workflow, run_id
        )
        summary = run_triage(repo=repo, workflow=workflow, run_id=run_id)
        key = save_to_s3(
            summary=summary,
            repo=repo,
            workflow=workflow,
            run_id=run_id,
            conclusion=conclusion,
        )
        logger.info("Triage saved to S3: %s", key)

    return {"status": "received"}


handler = Mangum(app)