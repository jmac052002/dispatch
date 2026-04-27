import boto3 
import requests 
import os 
from datetime import datetime, timezone, timedelta 

def get_cloudwatch_logs(log_group: str, minutes: int) -> str:
    client = boto3.client("logs", region_name="us-east-1")
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes)

    try:
        response = client.filter_log_events(
            logGroupName=log_group,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            limit=50
        )

        events = response.get("events", [])

        if not events:
            return f"No log events found in {log_group} for the last {minutes} minutes."

        lines = []
        for event in events:
            timestamp = datetime.fromtimestamp(
                event["timestamp"] / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"{timestamp} {event['message'].strip()}")

        return "\n".join(lines)

    except client.exceptions.ResourceNotFoundException:
        return f"Log group {log_group} does not exist."
    except Exception as e:
        return f"Error fetching logs: {str(e)}"
    
def get_github_workflow_logs(repo: str, run_id: int) -> str:
    token = os.getenv("GITHUB_TOKEN", "")

    if not token:
        return "Error: GITHUB_TOKEN not configured."

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        run_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
        run_response = requests.get(run_url, headers=headers)
        run_response.raise_for_status()
        run_data = run_response.json()

        conclusion = run_data.get("conclusion", "unknown")
        status = run_data.get("status", "unknown")
        workflow_name = run_data.get("name", "unknown")
        created_at = run_data.get("created_at", "unknown")
        html_url = run_data.get("html_url", "")

        jobs_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
        jobs_response = requests.get(jobs_url, headers=headers)
        jobs_response.raise_for_status()
        jobs_data = jobs_response.json()

        failed_steps = []
        for job in jobs_data.get("jobs", []):
            if job.get("conclusion") == "failure":
                for step in job.get("steps", []):
                    if step.get("conclusion") == "failure":
                        failed_steps.append(
                            f"Job: {job['name']} | Step: {step['name']}"
                        )

        summary = (
            f"Workflow: {workflow_name}\n"
            f"Status: {status} | Conclusion: {conclusion}\n"
            f"Started: {created_at}\n"
            f"URL: {html_url}\n"
        )

        if failed_steps:
            summary += "Failed steps:\n" + "\n".join(failed_steps)
        else:
            summary += "No individual failed steps identified."

        return summary

    except requests.exceptions.HTTPError as e:
        return f"GitHub API error: {e.response.status_code} — {e.response.text}"
    except Exception as e:
        return f"Error fetching workflow run: {str(e)}"
    
def get_ecs_service_status(cluster: str, service: str) -> str:
    client = boto3.client("ecs", region_name="us-east-1")

    try:
        response = client.describe_services(
            cluster=cluster,
            services=[service]
        )

        services = response.get("services", [])

        if not services:
            return f"No service '{service}' found in cluster '{cluster}'."

        svc = services[0]
        status = svc.get("status", "unknown")
        running = svc.get("runningCount", 0)
        desired = svc.get("desiredCount", 0)
        pending = svc.get("pendingCount", 0)
        task_def = svc.get("taskDefinition", "unknown").split("/")[-1]

        deployments = svc.get("deployments", [])
        deployment_info = []
        for d in deployments:
            deployment_info.append(
                f"  [{d.get('status')}] running={d.get('runningCount')} "
                f"desired={d.get('desiredCount')} "
                f"failed={d.get('failedTasks', 0)}"
            )

        events = svc.get("events", [])[:3]
        recent_events = [e.get("message", "") for e in events]

        summary = (
            f"Service: {service}\n"
            f"Cluster: {cluster}\n"
            f"Status: {status}\n"
            f"Tasks — running: {running} | desired: {desired} | pending: {pending}\n"
            f"Task definition: {task_def}\n"
        )

        if deployment_info:
            summary += "Deployments:\n" + "\n".join(deployment_info) + "\n"

        if recent_events:
            summary += "Recent events:\n" + "\n".join(recent_events)

        return summary

    except client.exceptions.ClusterNotFoundException:
        return f"Cluster '{cluster}' not found."
    except Exception as e:
        return f"Error fetching ECS service status: {str(e)}"
    
TOOL_DEFINITIONS = [
    {
        "name": "get_cloudwatch_logs",
        "description": "Fetches recent log events from a CloudWatch log group to help investigate incidents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "log_group": {
                    "type": "string",
                    "description": "The CloudWatch log group name to fetch logs from."
                },
                "minutes": {
                    "type": "integer",
                    "description": "How many minutes back to fetch logs from."
                }
            },
            "required": ["log_group", "minutes"]
        }
    },
    {
        "name": "get_github_workflow_logs",
        "description": "Fetches details and failed steps from a GitHub Actions workflow run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "The GitHub repository in owner/repo format."
                },
                "run_id": {
                    "type": "integer",
                    "description": "The GitHub Actions workflow run ID."
                }
            },
            "required": ["repo", "run_id"]
        }
    },
    {
        "name": "get_ecs_service_status",
        "description": "Describes the current status of an ECS service including running task counts and recent events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cluster": {
                    "type": "string",
                    "description": "The ECS cluster name."
                },
                "service": {
                    "type": "string",
                    "description": "The ECS service name."
                }
            },
            "required": ["cluster", "service"]
        }
    }
]
    
    
    
    
    
    