from fastmcp import FastMCP

from mcp_server.tools.cloudwatch import register_cloudwatch_tools
from mcp_server.tools.github import register_github_tools
from mcp_server.tools.ecs import register_ecs_tools

mcp = FastMCP(
    name="dispatch_mcp",
    instructions=(
        "You are the Dispatch incident triage assistant. "
        "Use these tools to investigate GitHub Actions failures, "
        "CloudWatch alarms, and ECS/EC2 service health."
    ),
)

register_cloudwatch_tools(mcp)
register_github_tools(mcp)
register_ecs_tools(mcp)


if __name__ == "__main__":
    mcp.run()