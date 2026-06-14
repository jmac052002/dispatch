import logging

from mangum import Mangum

from output import save_to_s3
from slack_output import post_to_slack 
from triage import run_triage
from webhook import app

logger = logging.getLogger(__name__)

_mangum = Mangum(app)


def handler(event, context):
    """Lambda entry point — routes webhook events and async triage events."""

    if event.get("dispatch_action") == "triage":
        repo = event["repo"]
        workflow = event["workflow"]
        run_id = event["run_id"]
        conclusion = event["conclusion"]

        logger.info(
            "Async triage received: repo=%s, run_id=%s", repo, run_id
        )
        summary = run_triage(repo=repo, workflow=workflow, run_id=run_id)
        key = save_to_s3(
            summary=summary,
            repo=repo,
            workflow=workflow,
            run_id=run_id,
            conclusion=conclusion,
        )
        post_to_slack(
            summary=summary,
            repo=repo,
            workflow=workflow,
            run_id=run_id,
            conclusion=conclusion,
       )
        logger.info("Async triage complete: %s", key)
        return {"status": "triaged", "key": key}

    # Everything else is an API Gateway event
    return _mangum(event, context) 