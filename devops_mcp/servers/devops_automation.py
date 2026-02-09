"""
DevOps Automation MCP Server
Wraps existing FastAPI deployment orchestration with MCP protocol

This server exposes your existing deployment workflows as MCP tools,
allowing AI to trigger deployments through natural language.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Import shared utilities
from devops_mcp.shared.api_client import FastAPIClient
from devops_mcp.config.settings import settings
from devops_mcp.tools.deployment_tools import get_deployment_tools

# Map FastAPI log levels to MCP LoggingLevel
_LEVEL_MAP = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "critical",
}


async def _send_log(message: str, level: str = "INFO") -> None:
    """Send a real-time log notification to the MCP client."""
    try:
        mcp_level = _LEVEL_MAP.get(level.upper(), "info")
        await app.request_context.session.send_log_message(
            level=mcp_level, data=message, logger="devops-automation"
        )
    except Exception:
        pass  # Don't let notification failures break the tool


# Initialize MCP server
app = Server("devops-automation")

# Initialize API client
api_client = FastAPIClient(
    base_url=settings.FASTAPI_URL,
    token=settings.API_TOKEN
)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available deployment tools
    
    Returns tool definitions from the tools module
    """
    return get_deployment_tools()


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Execute deployment tools
    
    Routes tool calls to appropriate handlers
    """
    
    if name == "deploy_microservice":
        return await deploy_microservice(arguments)
    
    elif name == "check_deployment_status":
        return await check_deployment_status(arguments)
    
    elif name == "get_deployment_plan":
        return await get_deployment_plan(arguments)
    
    elif name == "list_recent_deployments":
        return await list_recent_deployments(arguments)
    
    elif name == "cleanup_deployment":
        return await cleanup_deployment(arguments)

    elif name == "rollback_deployment":
        return await rollback_deployment(arguments)

    elif name == "quick_deploy_microservice":
        return await quick_deploy_microservice(arguments)

    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def deploy_microservice(arguments: dict) -> list[TextContent]:
    """
    Deploy microservice by calling the streaming FastAPI endpoint
    
    This calls your existing /gitops/micro-service endpoint and
    processes the streaming response.
    """
    # Build payload using snake_case field names (Pydantic v2 with populate_by_name)
    payload = {
        "environment": arguments["environment"],
        "microservice_name": arguments["microservice_name"],
        "microservice_url": arguments["microservice_url"],
        "container_port": arguments["container_port"],
        "gitops_repo_url": arguments["gitops_repo_url"],
        "git_repo_name": arguments["git_repo_name"],
        "git_branch": arguments.get("git_branch", "main"),
        "argocd_app_name": arguments["argocd_app_name"],
        "domain_name": arguments["domain_name"],
    }
    # Only include optional fields when provided
    if arguments.get("env_content"):
        payload["env_content"] = arguments["env_content"]
    if arguments.get("cronjobs"):
        payload["cronjobs"] = arguments["cronjobs"]
    if arguments.get("worker"):
        payload["worker"] = arguments["worker"]
    
    try:
        # Stream the deployment
        logs = []
        result_data = None
        error_message = None
        
        async for event in api_client.stream_post("/api/gitops/micro-service", payload):
            event_type = event.get("type")

            if event_type == "log":
                log_msg = event.get("message", "")
                log_level = event.get("level", "INFO")
                logs.append(log_msg)
                await _send_log(log_msg, log_level)

            elif event_type == "result":
                result_data = event.get("data")

            elif event_type == "error":
                error_message = event.get("message")
        
        # Format response
        if error_message:
            return [TextContent(
                type="text",
                text=f"❌ Deployment failed: {error_message}\n\n"
                     f"Recent logs:\n" + "\n".join(logs[-20:])
            )]
        
        if result_data:
            # Deployment successful
            status = result_data.get("status", "unknown")
            message = result_data.get("message", "")
            microservice = result_data.get("microservice_name", "")
            environment = result_data.get("environment", "")
            
            response_text = f"✅ Deployment Successful!\n\n"
            response_text += f"**Service:** {microservice}\n"
            response_text += f"**Environment:** {environment}\n"
            response_text += f"**Status:** {status}\n"
            response_text += f"**Message:** {message}\n\n"
            
            # Add deployment details
            if result_data.get("domain_name"):
                response_text += f"**Access URL:** https://{result_data['domain_name']}\n"
            
            return [TextContent(type="text", text=response_text)]
        
        # Fallback
        return [TextContent(
            type="text",
            text="⚠️ Deployment completed but no result received."
        )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Deployment error: {str(e)}"
        )]


async def check_deployment_status(arguments: dict) -> list[TextContent]:
    """Check status of an ArgoCD application"""
    app_name = arguments["argocd_app_name"]

    try:
        response = await api_client.get(
            f"/api/argocd/applications/{app_name}/status"
        )

        # Response is BaseResponse wrapper — extract .data
        data = response.get("data", {})

        # Format status response
        status_text = f"**Application Status: {data.get('name', app_name)}**\n\n"
        status_text += f"Sync Status: {data.get('sync', 'unknown')}\n"
        status_text += f"Health Status: {data.get('health', 'unknown')}\n"

        resources = data.get('resources', [])
        if resources:
            status_text += f"\n**Resources ({len(resources)}):**\n"
            for res in resources:
                kind = res.get('kind', 'Unknown')
                name = res.get('name', 'unknown')
                health = res.get('health', 'N/A')
                status_text += f"  - {kind}/{name}: {health}\n"

        return [TextContent(type="text", text=status_text)]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error checking status: {str(e)}"
        )]


async def get_deployment_plan(arguments: dict) -> list[TextContent]:
    """Get deployment plan (dry-run)"""
    plan_text = f"""
**Deployment Plan (Dry Run)**

Service: {arguments['microservice_name']}
Environment: {arguments['environment']}
Microservice Repo: {arguments['microservice_url']}
GitOps Repo: {arguments['gitops_repo_url']}

**Planned Steps:**

1. **Generate Manifests**
   - Process Helm templates
   - Inject environment variables
   - Create Kubernetes resources

2. **Update GitOps Repository**
   - Clone {arguments['gitops_repo_url']}
   - Commit manifests to {arguments['environment']} branch
   - Push changes

3. **Configure GitHub Workflows**
   - Clone microservice repository
   - Add CI/CD workflow for {arguments['environment']}
   - Create repository secrets

4. **DNS Configuration**
   - Create Cloudflare A record
   - Point to GKE ingress IP

5. **Monitor CI/CD**
   - Wait for GitHub Action to complete
   - Verify container build and push

6. **ArgoCD Deployment**
   - Create ArgoCD application
   - Sync to Kubernetes cluster
   - Monitor health status

**No changes will be made until you execute deploy_microservice.**
"""
    
    return [TextContent(type="text", text=plan_text)]


async def list_recent_deployments(arguments: dict) -> list[TextContent]:
    """List ArgoCD applications"""
    try:
        params = {}
        if arguments.get("project"):
            params["project"] = arguments["project"]
        if arguments.get("repo"):
            params["repo"] = arguments["repo"]
        if arguments.get("sync_status"):
            params["sync_status"] = arguments["sync_status"]
        if arguments.get("health_status"):
            params["health_status"] = arguments["health_status"]

        # Response is ApplicationListResponse directly (not BaseResponse wrapped)
        data = await api_client.get("/api/argocd/applications", params=params)

        items = data.get("items", [])
        total = data.get("total", len(items))

        if not items:
            return [TextContent(type="text", text="No ArgoCD applications found.")]

        result = f"**ArgoCD Applications ({total} total):**\n\n"
        for app in items:
            name = app.get("name", "unknown")
            sync = app.get("sync", "N/A")
            health = app.get("health", "N/A")
            project = app.get("project", "N/A")
            result += f"- **{name}** (project: {project})\n"
            result += f"  Sync: {sync} | Health: {health}\n"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def rollback_deployment(arguments: dict) -> list[TextContent]:
    """Rollback an ArgoCD application to a specific revision"""
    app_name = arguments["argocd_app_name"]
    revision = arguments["revision"]

    try:
        result = await api_client.post(
            f"/api/argocd/applications/{app_name}/rollback",
            data={"revision": revision}
        )

        # Response is BaseResponse wrapper
        status = result.get("status", "unknown")
        message = result.get("message", "")
        data = result.get("data", {})

        response_text = f"Rollback for {app_name}\n\n"
        response_text += f"Status: {status}\n"
        response_text += f"Message: {message}\n"
        if data:
            response_text += f"Details: {data}\n"

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def cleanup_deployment(arguments: dict) -> list[TextContent]:
    """Cleanup all resources created by a deployment"""
    payload = {
        "microservice_name": arguments["microservice_name"],
        "environment": arguments["environment"],
        "domain_name": arguments["domain_name"],
        "argocd_app_name": arguments["argocd_app_name"],
        "gitops_repo_url": arguments["gitops_repo_url"],
        "microservice_repo_url": arguments["microservice_repo_url"],
        "force": arguments.get("force", False),
    }
    if arguments.get("github_secret_names"):
        payload["github_secret_names"] = arguments["github_secret_names"]
    if arguments.get("audit_comment"):
        payload["audit_comment"] = arguments["audit_comment"]

    try:
        logs = []
        result_data = None
        error_message = None

        async for event in api_client.stream_post("/api/gitops/cleanup", payload):
            event_type = event.get("type")

            if event_type == "log":
                log_msg = event.get("message", "")
                log_level = event.get("level", "INFO")
                logs.append(log_msg)
                await _send_log(log_msg, log_level)
            elif event_type == "result":
                result_data = event.get("data")
            elif event_type == "error":
                error_message = event.get("message")

        if error_message:
            return [TextContent(
                type="text",
                text=f"Cleanup failed: {error_message}\n\n"
                     f"Recent logs:\n" + "\n".join(logs[-20:])
            )]

        if result_data:
            success = result_data.get("success", False)
            status_icon = "Cleanup successful" if success else "Cleanup completed with issues"
            response_text = f"**{status_icon}**\n\n"
            response_text += f"**Service:** {arguments['microservice_name']}\n"
            response_text += f"**Environment:** {arguments['environment']}\n\n"

            steps = result_data.get("steps", {})
            if steps:
                response_text += "**Results:**\n"
                for step_name, step_result in steps.items():
                    response_text += f"  - {step_name}: {step_result}\n"

            return [TextContent(type="text", text=response_text)]

        return [TextContent(
            type="text",
            text="Cleanup completed but no result received."
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Cleanup error: {str(e)}"
        )]


def _extract_repo_name(github_url: str) -> str:
    """
    Extract repository name from GitHub URL.

    Examples:
        https://github.com/tehvault/poc-star -> poc-star
        https://github.com/tehvault/poc-star.git -> poc-star
        https://github.com/tehvault/user-service/ -> user-service
    """
    # Remove trailing slash and .git suffix
    url = github_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Extract last path segment
    return url.split("/")[-1]


async def quick_deploy_microservice(arguments: dict) -> list[TextContent]:
    """
    Simplified deployment requiring only environment and GitHub URL.

    Derives all other parameters and delegates to deploy_microservice.
    Mirrors the frontend handleProceed logic from GitHubDeployPage.tsx.
    """
    environment = arguments["environment"]
    microservice_github_url = arguments["microservice_github_url"]

    # Extract microservice name from URL
    microservice_name = _extract_repo_name(microservice_github_url)

    # Derive all parameters (matching frontend handleProceed logic)
    derived_arguments = {
        "environment": environment,
        "microservice_name": microservice_name,
        "microservice_url": microservice_github_url,
        "container_port": arguments.get("container_port", settings.DEFAULT_CONTAINER_PORT),
        "gitops_repo_url": f"{settings.GITHUB_BASE_URL}/{settings.GITOPS_REPO_NAME}.git",
        "git_repo_name": microservice_name,
        "git_branch": environment,  # Branch matches environment
        "argocd_app_name": f"{microservice_name}-{environment}",
        "domain_name": f"{microservice_name}-{environment}.{settings.DOMAIN_SUFFIX}",
    }

    # Pass through optional env_content if provided
    if arguments.get("env_content"):
        derived_arguments["env_content"] = arguments["env_content"]

    # Delegate to existing deploy_microservice
    return await deploy_microservice(derived_arguments)


async def main():
    """Run the MCP server"""
    import logging
    logger = logging.getLogger(__name__)

    # Check FastAPI connection
    if not await api_client.health_check():
        logger.warning(f"Cannot connect to FastAPI at {settings.FASTAPI_URL}")
        logger.warning("Server will start but may not function correctly.")

    # Run server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())