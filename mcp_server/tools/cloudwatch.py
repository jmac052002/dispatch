import json 
import time
from datetime import datetime, timezone
 
import boto3
from botocore.exceptions import BotoCoreError, ClientError 
from fastmcp import FastMCP 
from pydantic import BaseModel, ConfigDict, Field 

from mcp_server.config import AWS_REGION 

class QueryLogsInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    log_group: str = Field(
        ...,
        description="CloudWatch log group name (e.g. '/aws/lambda/dispatch-api')",
        min_length=1,
        max_length=512,
    )
    query_string: str = Field(
        ...,
        description="CloudWatch Logs Insights query (e.g. 'fields @timestamp, @message | filter @message like /ERROR/ | limit 20')",
        min_length=1,
    )
    lookback_minutes: int = Field(
        default=30,
        description="How many minutes back to query (default: 30)",
        ge=1,
        le=1440,
    )


class GetAlarmsInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    state: str = Field(
        default="ALARM",
        description="Alarm state to filter by: ALARM, OK, or INSUFFICIENT_DATA",
        pattern="^(ALARM|OK|INSUFFICIENT_DATA)$",
    )
    
def _format_timestamp(dt: datetime) -> str:
    """Format a datetime to a readable UTC string."""
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC") 

def register_cloudwatch_tools(mcp: FastMCP) -> None:
    """Register all CloudWatch tools with the MCP server."""

    @mcp.tool(
        name="cloudwatch_query_logs",
        annotations={
            "title": "Query CloudWatch Logs",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def cloudwatch_query_logs(params: QueryLogsInput) -> str:
        """Run a CloudWatch Logs Insights query and return matching log events.

        Use this to investigate errors, exceptions, or specific patterns in
        Lambda, ECS, or API Gateway log groups.

        Args:
            params (QueryLogsInput):
                - log_group (str): Log group name to query
                - query_string (str): Logs Insights query string
                - lookback_minutes (int): How far back to search (1–1440)

        Returns:
            str: JSON with query results or an error message.
        """
        client = boto3.client("logs", region_name=AWS_REGION)

        end_time = datetime.now(timezone.utc)
        start_time_epoch = int(
            (end_time.timestamp() - params.lookback_minutes * 60)
        )
        end_time_epoch = int(end_time.timestamp())

        try:
            response = client.start_query(
                logGroupName=params.log_group,
                startTime=start_time_epoch,
                endTime=end_time_epoch,
                queryString=params.query_string,
            )
            query_id = response["queryId"]

            # Poll until complete
            for _ in range(20):
                result = client.get_query_results(queryId=query_id)
                if result["status"] in ("Complete", "Failed", "Cancelled"):
                    break
                time.sleep(1)

            if result["status"] != "Complete":
                return json.dumps({
                    "error": f"Query ended with status: {result['status']}"
                })

            rows = [
                {field["field"]: field["value"] for field in row}
                for row in result["results"]
            ]

            return json.dumps({
                "log_group": params.log_group,
                "query": params.query_string,
                "lookback_minutes": params.lookback_minutes,
                "result_count": len(rows),
                "results": rows,
            }, indent=2)

        except ClientError as e:
            return json.dumps({
                "error": e.response["Error"]["Message"],
                "code": e.response["Error"]["Code"],
            })
        except BotoCoreError as e:
            return json.dumps({"error": f"AWS connection error: {str(e)}"})

    @mcp.tool(
        name="cloudwatch_get_alarms",
        annotations={
            "title": "Get CloudWatch Alarms",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def cloudwatch_get_alarms(params: GetAlarmsInput) -> str:
        """Return CloudWatch alarms filtered by state.

        Use this to get a snapshot of what is currently firing (ALARM),
        healthy (OK), or missing data (INSUFFICIENT_DATA).

        Args:
            params (GetAlarmsInput):
                - state (str): ALARM | OK | INSUFFICIENT_DATA

        Returns:
            str: JSON list of matching alarms with name, state, and reason.
        """
        client = boto3.client("cloudwatch", region_name=AWS_REGION)

        try:
            response = client.describe_alarms(StateValue=params.state)
            alarms = [
                {
                    "name": a["AlarmName"],
                    "state": a["StateValue"],
                    "reason": a.get("StateReason", ""),
                    "updated": _format_timestamp(a["StateUpdatedTimestamp"]),
                    "metric": a.get("MetricName", ""),
                    "namespace": a.get("Namespace", ""),
                }
                for a in response.get("MetricAlarms", [])
            ]

            return json.dumps({
                "state_filter": params.state,
                "count": len(alarms),
                "alarms": alarms,
            }, indent=2)

        except ClientError as e:
            return json.dumps({
                "error": e.response["Error"]["Message"],
                "code": e.response["Error"]["Code"],
            })
        except BotoCoreError as e:
            return json.dumps({"error": f"AWS connection error: {str(e)}"})