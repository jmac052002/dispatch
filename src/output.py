import json
import os
import boto3
from datetime import datetime, timezone


def save_to_s3(
    summary: str,
    repo: str,
    workflow: str,
    run_id: int,
    conclusion: str,
    bucket: str | None = None,
) -> str:
    """Save a triage summary to S3 as a JSON record.

    Args:
        summary: Claude's triage analysis
        repo: GitHub repository in owner/repo format
        workflow: Name of the failed workflow
        run_id: GitHub Actions workflow run ID
        conclusion: Workflow conclusion (e.g. 'failure')
        bucket: S3 bucket name (defaults to TRIAGE_BUCKET env var)

    Returns:
        str: The S3 key the record was written to
    """
    bucket_name = bucket or os.getenv("TRIAGE_BUCKET")
    if not bucket_name:
        raise EnvironmentError(
            "S3 bucket not specified. Set TRIAGE_BUCKET environment variable."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    safe_repo = repo.replace("/", "_")
    key = f"triage/{safe_repo}/{timestamp}-{run_id}.json"

    record = {
        "timestamp": timestamp,
        "repo": repo,
        "workflow": workflow,
        "run_id": run_id,
        "conclusion": conclusion,
        "summary": summary,
    }

    client = boto3.client("s3")
    client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(record, indent=2),
        ContentType="application/json",
    )

    return key