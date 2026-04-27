import anthropic
import os
from dotenv import load_dotenv
from tools import get_cloudwatch_logs, get_github_workflow_logs, get_ecs_service_status, TOOL_DEFINITIONS 

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

tools = TOOL_DEFINITIONS

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

def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_cloudwatch_logs":
        return get_cloudwatch_logs(**tool_input)
    elif tool_name == "get_github_workflow_logs":
        return get_github_workflow_logs(**tool_input)
    elif tool_name == "get_ecs_service_status":
        return get_ecs_service_status(**tool_input)
    else:
        return f"Unknown tool: {tool_name}"

tool_use_block = next(
    block for block in response.content
    if block.type == "tool_use"
)

tool_result = run_tool(tool_use_block.name, tool_use_block.input)

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