import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

tools = [
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
    }
]

messages = [
    {
        "role": "user",
        "content": "I'm seeing errors in my ECS service. Can you check the logs in /ecs/dispatch-api for the last 30 minutes?"
    }
]

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

print("Stop reason:", response.stop_reason)
print("Response content:", response.content)

def get_cloudwatch_logs(log_group: str, minutes: int) -> str:
    # Mock response for now — real boto3 call comes in Phase 3
    return f"[MOCK] Last {minutes} minutes of logs from {log_group}:\n2025-04-25 11:10:01 ERROR Connection timeout to database\n2025-04-25 11:10:45 ERROR Retry attempt 1 failed"

tool_use_block = response.content[0]

tool_result = get_cloudwatch_logs(
    log_group=tool_use_block.input["log_group"],
    minutes=tool_use_block.input["minutes"]
)

messages.append({"role": "assistant", "content": response.content})
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": tool_use_block.id,
            "content": tool_result
        }
    ]
})

final_response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

print("\n--- Final Response ---")
print(final_response.content[0].text)