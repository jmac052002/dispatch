import logging
import os

import requests

logger = logging.getLogger(__name__)


def post_to_slack(summary: str, repo: str, workflow: str, run_id: int, conclusion: str) -> bool:
    """Post a triage summary to Slack via incoming webhook.

    Returns:
        bool: True if message posted successfully, False otherwise
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not set - skipping Slack notification")
        return False

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":rotating_light: Dispatch Triage — {workflow}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Repo:*\n{repo}"},
                    {"type": "mrkdwn", "text": f"*Conclusion:*\n{conclusion}"},
                    {"type": "mrkdwn", "text": f"*Run ID:*\n{run_id}"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Triage Summary:*\n{summary[:2900]}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Run"},
                        "url": f"https://github.com/{repo}/actions/runs/{run_id}"
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        response.raise_for_status()
        logger.info("Slack notification sent for run_id=%s", run_id)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Failed to post to Slack: %s", str(e))
        return False 