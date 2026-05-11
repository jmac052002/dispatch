import os
import anthropic
from dotenv import load_dotenv
from tools import (
    get_cloudwatch_logs,
    get_github_workflow_logs,
    get_ecs_service_status,
    TOOL_DEFINITIONS,
) 

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
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
        tools=tools.TOOL_DEFINITIONS,
        messages=messages,
    )

    while response.stop_reason == "tool_use":
        tool_use_block = next(
            block for block in response.content if block.type == "tool_use"
        )

        tool_result = _run_tool(tool_use_block.name, tool_use_block.input)

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": tool_result,
                }
            ],
        })

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            tools=tools.TOOL_DEFINITIONS,
            messages=messages,
        )

    final_text = next(
        block.text for block in response.content if hasattr(block, "text")
    )
    return final_text


def _run_tool(tool_name: str, tool_input: dict) -> str:
    """Route a tool call to the correct implementation."""
    if tool_name == "get_cloudwatch_logs":
        return tools.get_cloudwatch_logs(**tool_input)
    elif tool_name == "get_github_workflow_logs":
        return tools.get_github_workflow_logs(**tool_input)
    elif tool_name == "get_ecs_service_status":
        return tools.get_ecs_service_status(**tool_input)
    else:
        return f"Unknown tool: {tool_name}"