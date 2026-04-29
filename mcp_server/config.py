import os


def get_required_env(key: str) -> str:
    """Load a required environment variable or raise a clear error."""
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Add it to your Claude Desktop MCP server env config."
        )
    return value


# AWS
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")

# GitHub
GITHUB_TOKEN: str = get_required_env("GITHUB_TOKEN")
GITHUB_REPO: str = get_required_env("GITHUB_REPO")  # format: owner/repo

# Timeouts (seconds)
HTTP_TIMEOUT: int = 10