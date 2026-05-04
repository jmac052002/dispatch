import json

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.config import GITHUB_TOKEN, GITHUB_REPO, HTTP_TIMEOUT 

GITHUB_API_BASE = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
} 

class GetWorkflowRunInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    repo: str = Field(
        default=GITHUB_REPO,
        description="GitHub repository in owner/repo format (defaults to configured repo)",
        min_length=1,
    )
    run_id: int = Field(
        ...,
        description="The GitHub Actions workflow run ID",
        gt=0,
    )


class ListFailedRunsInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    repo: str = Field(
        default=GITHUB_REPO,
        description="GitHub repository in owner/repo format (defaults to configured repo)",
        min_length=1,
    )
    limit: int = Field(
        default=5,
        description="Maximum number of failed runs to return (1–20)",
        ge=1,
        le=20,
    ) 
    
def register_github_tools(mcp: FastMCP) -> None:
    """Register all GitHub tools with the MCP server."""

    @mcp.tool(
        name="github_get_workflow_run",
        annotations={
            "title": "Get GitHub Workflow Run",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def github_get_workflow_run(params: GetWorkflowRunInput) -> str:
        """Fetch details and failed steps for a GitHub Actions workflow run.

        Use this to investigate a specific run ID after a webhook fires,
        or when Claude Desktop is asked about a known failure.

        Args:
            params (GetWorkflowRunInput):
                - repo (str): owner/repo format
                - run_id (int): workflow run ID

        Returns:
            str: JSON with workflow name, status, conclusion, and failed steps.
        """
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                run_resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{params.repo}/actions/runs/{params.run_id}",
                    headers=HEADERS,
                )
                run_resp.raise_for_status()
                run = run_resp.json()

                jobs_resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{params.repo}/actions/runs/{params.run_id}/jobs",
                    headers=HEADERS,
                )
                jobs_resp.raise_for_status()
                jobs = jobs_resp.json().get("jobs", [])

                failed_steps = [
                    {
                        "job": job["name"],
                        "step": step["name"],
                        "number": step["number"],
                    }
                    for job in jobs
                    if job.get("conclusion") == "failure"
                    for step in job.get("steps", [])
                    if step.get("conclusion") == "failure"
                ]

                return json.dumps({
                    "repo": params.repo,
                    "run_id": params.run_id,
                    "workflow": run.get("name"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "started_at": run.get("created_at"),
                    "url": run.get("html_url"),
                    "failed_steps": failed_steps,
                }, indent=2)

            except httpx.HTTPStatusError as e:
                return json.dumps({
                    "error": f"GitHub API error: {e.response.status_code}",
                    "detail": e.response.text,
                })
            except httpx.TimeoutException:
                return json.dumps({"error": "Request timed out reaching GitHub API"})

    @mcp.tool(
        name="github_list_failed_runs",
        annotations={
            "title": "List Recent Failed Workflow Runs",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def github_list_failed_runs(params: ListFailedRunsInput) -> str:
        """List the most recent failed GitHub Actions workflow runs.

        Use this for a broad view — when you want to know what has been
        failing recently without knowing a specific run ID.

        Args:
            params (ListFailedRunsInput):
                - repo (str): owner/repo format
                - limit (int): how many results to return (1–20)

        Returns:
            str: JSON list of failed runs with name, ID, and URL.
        """
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{params.repo}/actions/runs",
                    headers=HEADERS,
                    params={"status": "failure", "per_page": params.limit},
                )
                resp.raise_for_status()
                runs = resp.json().get("workflow_runs", [])

                return json.dumps({
                    "repo": params.repo,
                    "count": len(runs),
                    "runs": [
                        {
                            "run_id": r["id"],
                            "workflow": r["name"],
                            "conclusion": r["conclusion"],
                            "started_at": r["created_at"],
                            "url": r["html_url"],
                        }
                        for r in runs
                    ],
                }, indent=2)

            except httpx.HTTPStatusError as e:
                return json.dumps({
                    "error": f"GitHub API error: {e.response.status_code}",
                    "detail": e.response.text,
                })
            except httpx.TimeoutException:
                return json.dumps({"error": "Request timed out reaching GitHub API"})