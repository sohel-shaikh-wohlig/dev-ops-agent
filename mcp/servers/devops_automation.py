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
from mcp.shared.api_client import FastAPIClient
from mcp.config.settings import settings
from mcp.tools.deployment_tools import get_deployment_tools

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
    
    elif name == "rollback_deployment":
        return await rollback_deployment(arguments)
    
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
    # Convert to FastAPI format (camelCase)
    payload = {
        "environment": arguments["environment"],
        "microserviceName": arguments["microservice_name"],
        "microserviceUrl": arguments["microservice_url"],
        "containerPort": arguments["container_port"],
        "gitOpsRepoUrl": arguments["gitops_repo_url"],
        "gitRepoName": arguments["git_repo_name"],
        "gitBranch": arguments.get("git_branch", "main"),
        "argoCdAppName": arguments["argocd_app_name"],
        "domainName": arguments["domain_name"],
        "envContent": arguments.get("env_content"),
        "cronjob": arguments.get("cronjob")
    }
    
    try:
        # Stream the deployment
        logs = []
        result_data = None
        error_message = None
        
        async for event in api_client.stream_post("/gitops/micro-service", payload):
            event_type = event.get("type")
            
            if event_type == "log":
                # Collect log messages
                log_msg = event.get("message", "")
                logs.append(log_msg)
            
            elif event_type == "result":
                # Final result
                result_data = event.get("data")
            
            elif event_type == "error":
                # Error occurred
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
    """Check status of a deployment"""
    microservice = arguments["microservice_name"]
    environment = arguments["environment"]
    
    try:
        data = await api_client.get(
            f"/gitops/deployments/{microservice}/{environment}"
        )
        
        # Format status response
        status_text = f"**Deployment Status: {microservice}**\n\n"
        status_text += f"Environment: {environment}\n"
        status_text += f"Status: {data.get('status', 'unknown')}\n"
        status_text += f"Last Updated: {data.get('last_updated', 'N/A')}\n"
        
        if data.get('current_step'):
            status_text += f"\nCurrent Step: {data['current_step']}\n"
        
        if data.get('argocd_sync_status'):
            status_text += f"ArgoCD Sync: {data['argocd_sync_status']}\n"
        
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
    """List recent deployments"""
    try:
        limit = arguments.get("limit", 10)
        environment = arguments.get("environment")
        
        params = {"limit": limit}
        if environment:
            params["environment"] = environment
        
        deployments = await api_client.get("/gitops/deployments", params=params)
        
        if not deployments:
            return [TextContent(type="text", text="No recent deployments found.")]
        
        # Format list
        result = "**Recent Deployments:**\n\n"
        for dep in deployments:
            result += f"• **{dep['microservice_name']}** ({dep['environment']})\n"
            result += f"  Status: {dep['status']}\n"
            result += f"  Deployed: {dep['created_at']}\n"
            result += f"  URL: {dep.get('domain_name', 'N/A')}\n\n"
        
        return [TextContent(type="text", text=result)]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def rollback_deployment(arguments: dict) -> list[TextContent]:
    """Rollback a deployment"""
    microservice = arguments["microservice_name"]
    environment = arguments["environment"]
    
    try:
        result = await api_client.post(
            f"/gitops/deployments/{microservice}/{environment}/rollback",
            data={}
        )
        
        response_text = f"✅ Rollback initiated for {microservice} in {environment}\n\n"
        response_text += f"Previous version: {result.get('previous_version', 'unknown')}\n"
        response_text += f"Current version: {result.get('current_version', 'unknown')}\n"
        
        return [TextContent(type="text", text=response_text)]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    # Check FastAPI connection
    if not await api_client.health_check():
        print(f"Warning: Cannot connect to FastAPI at {settings.FASTAPI_URL}")
        print("Server will start but may not function correctly.")
    
    # Run server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())