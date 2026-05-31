import logging
import os

import anthropic
from dotenv import load_dotenv
from tools import (
    get_cloudwatch_logs,
    get_github_workflow_logs,
    get_ecs_service_status,
    TOOL_DEFINITIONS,
) 

logger = logging.getLogger(__name__)
load_dotenv()


def run_triage(repo: str, workflow: str, run_id: int) -> str:
    """Invoke Claude with real tools to triage a CI/CD or infrastructure failure.

    Args:
        repo: GitHub repository in owner/repo format
        workflow: Name of the failed workflow
        run_id: GitHub Actions workflow run ID

    Returns:
        str: Claude's triage summary
    """
    logger.info("run_triage called: repo=%s, workflow=%s, run_id=%s", repo, workflow, run_id)
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=60,)

    messages = [
        {
            "role": "user",
            "content": (
                f"A GitHub Actions workflow failed. Investigate and summarize the root cause.\n\n"
                f"Repo: {repo}\n"
                f"Workflow: {workflow}\n"
                f"Run ID: {run_id}\n\n"
                f"Use the available tools to check the workflow run details, "
                f"relevant CloudWatch logs, and ECS service status if applicable. "
                f"Return a concise triage summary with probable cause and recommended fix."
            ),
        }
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        tools=TOOL_DEFINITIONS,
        messages=messages,
    )

    while response.stop_reason == "tool_use":
        # Collect ALL tool_use blocks — Claude can request several in one turn
        tool_use_blocks = [
            block for block in response.content if block.type == "tool_use"
        ]

        tool_results = []
        for tool_block in tool_use_blocks:
            logger.info("Calling tool: %s with input: %s", tool_block.name, tool_block.input)
            result = _run_tool(tool_block.name, tool_block.input)
            logger.info("Tool %s returned %d chars", tool_block.name, len(result))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

    final_text = next(
        block.text for block in response.content if block.type == "text"
    )
    return final_text

def _run_tool(tool_name: str, tool_input: dict) -> str:
    """Route a tool call to the correct implementation."""
    if tool_name == "get_cloudwatch_logs":
        return get_cloudwatch_logs(**tool_input)
    elif tool_name == "get_github_workflow_logs":
        return get_github_workflow_logs(**tool_input)
    elif tool_name == "get_ecs_service_status":
        return get_ecs_service_status(**tool_input)
    else:
        return f"Unknown tool: {tool_name}"