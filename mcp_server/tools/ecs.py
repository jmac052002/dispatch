import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.config import AWS_REGION 

class GetServiceStatusInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    cluster: str = Field(
        ...,
        description="ECS cluster name (e.g. 'dispatch-cluster')",
        min_length=1,
    )
    service: str = Field(
        ...,
        description="ECS service name (e.g. 'dispatch-api')",
        min_length=1,
    )


class ListServicesInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    cluster: str = Field(
        ...,
        description="ECS cluster name to list services from",
        min_length=1,
    ) 
    
def register_ecs_tools(mcp: FastMCP) -> None:
    """Register all ECS tools with the MCP server."""

    @mcp.tool(
        name="ecs_get_service_status",
        annotations={
            "title": "Get ECS Service Status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def ecs_get_service_status(params: GetServiceStatusInput) -> str:
        """Describe the current status of an ECS service.

        Returns running/desired/pending task counts, deployment status,
        and the three most recent service events. Use this to determine
        if a service is healthy, degraded, or failing to start tasks.

        Args:
            params (GetServiceStatusInput):
                - cluster (str): ECS cluster name
                - service (str): ECS service name

        Returns:
            str: JSON with task counts, deployments, and recent events.
        """
        client = boto3.client("ecs", region_name=AWS_REGION)

        try:
            response = client.describe_services(
                cluster=params.cluster,
                services=[params.service],
            )

            services = response.get("services", [])
            if not services:
                return json.dumps({
                    "error": f"Service '{params.service}' not found in cluster '{params.cluster}'"
                })

            svc = services[0]

            deployments = [
                {
                    "status": d.get("status"),
                    "running": d.get("runningCount"),
                    "desired": d.get("desiredCount"),
                    "failed_tasks": d.get("failedTasks", 0),
                    "task_definition": d.get("taskDefinition", "").split("/")[-1],
                }
                for d in svc.get("deployments", [])
            ]

            recent_events = [
                e.get("message", "")
                for e in svc.get("events", [])[:3]
            ]

            return json.dumps({
                "cluster": params.cluster,
                "service": params.service,
                "status": svc.get("status"),
                "running": svc.get("runningCount"),
                "desired": svc.get("desiredCount"),
                "pending": svc.get("pendingCount"),
                "task_definition": svc.get("taskDefinition", "").split("/")[-1],
                "deployments": deployments,
                "recent_events": recent_events,
            }, indent=2)

        except ClientError as e:
            return json.dumps({
                "error": e.response["Error"]["Message"],
                "code": e.response["Error"]["Code"],
            })
        except BotoCoreError as e:
            return json.dumps({"error": f"AWS connection error: {str(e)}"})

    @mcp.tool(
        name="ecs_list_services",
        annotations={
            "title": "List ECS Services in Cluster",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def ecs_list_services(params: ListServicesInput) -> str:
        """List all ECS services running in a cluster.

        Use this when you don't know the service name yet, or want a
        broad view of what's deployed in a cluster before drilling in.

        Args:
            params (ListServicesInput):
                - cluster (str): ECS cluster name

        Returns:
            str: JSON list of service ARNs in the cluster.
        """
        client = boto3.client("ecs", region_name=AWS_REGION)

        try:
            response = client.list_services(cluster=params.cluster)
            arns = response.get("serviceArns", [])

            services = [arn.split("/")[-1] for arn in arns]

            return json.dumps({
                "cluster": params.cluster,
                "count": len(services),
                "services": services,
            }, indent=2)

        except ClientError as e:
            return json.dumps({
                "error": e.response["Error"]["Message"],
                "code": e.response["Error"]["Code"],
            })
        except BotoCoreError as e:
            return json.dumps({"error": f"AWS connection error: {str(e)}"})