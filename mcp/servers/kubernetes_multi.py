"""
Kubernetes MCP wrapper with multi-cluster support
Allows AI to specify which cluster context to use

This MCP server enables Claude to interact with multiple GKE clusters
across different environments (dev, staging, production, uat) using
a single unified interface.

Usage:
    python k8s_multi_cluster_mcp.py

Configure your kubeconfig contexts first:
    kubectl config rename-context gke_project_region_dev dev
    kubectl config rename-context gke_project_region_staging uat
    kubectl config rename-context gke_project_region_prod production
    kubectl config rename-context gke_project_region_staging staging
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import subprocess
import json
import os
import sys

app = Server("kubernetes-multi")

# Available clusters/contexts
# Modify this to match your actual kubectl context names
CONTEXTS = {
    "dev": "dev",
    "development": "dev",
    "uat": "uat"
}

def run_kubectl(args: list, context: str = None) -> dict:
    """Run kubectl command with optional context"""
    cmd = ["kubectl"]
    
    if context:
        cmd.extend(["--context", context])
    
    cmd.extend(args)
    cmd.extend(["--output", "json"])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return {"success": True, "data": json.loads(result.stdout)}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON response"}


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="k8s_get_pods",
            description=f"""Get pods from Kubernetes cluster.
            
            Available environments: {', '.join(set(CONTEXTS.values()))}
            
            Examples:
            - Get all pods in dev: environment='dev'
            - Get pods in namespace: environment='staging', namespace='api'
            - Get specific pod: environment='prod', namespace='api', pod_name='user-service-abc'
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": list(set(CONTEXTS.values())),
                        "description": "Target environment (dev, staging, production, uat)"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Kubernetes namespace (optional, default: all)",
                        "default": ""
                    },
                    "pod_name": {
                        "type": "string",
                        "description": "Specific pod name (optional)",
                        "default": ""
                    }
                },
                "required": ["environment"]
            }
        ),
        
        Tool(
            name="k8s_get_deployments",
            description="Get deployments from specified environment",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": list(set(CONTEXTS.values())),
                        "description": "Target environment"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Kubernetes namespace",
                        "default": ""
                    }
                },
                "required": ["environment"]
            }
        ),
        
        Tool(
            name="k8s_get_services",
            description="Get services from specified environment",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": list(set(CONTEXTS.values())),
                        "description": "Target environment"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Kubernetes namespace",
                        "default": ""
                    }
                },
                "required": ["environment"]
            }
        ),
        
        Tool(
            name="k8s_get_namespaces",
            description="List all namespaces in specified environment",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": list(set(CONTEXTS.values())),
                        "description": "Target environment"
                    }
                },
                "required": ["environment"]
            }
        ),
        
        Tool(
            name="k8s_describe_pod",
            description="Get detailed information about a pod",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": list(set(CONTEXTS.values())),
                        "description": "Target environment"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Kubernetes namespace"
                    },
                    "pod_name": {
                        "type": "string",
                        "description": "Pod name"
                    }
                },
                "required": ["environment", "namespace", "pod_name"]
            }
        ),
        
        Tool(
            name="k8s_get_logs",
            description="Get logs from a pod",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": list(set(CONTEXTS.values())),
                        "description": "Target environment"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Kubernetes namespace"
                    },
                    "pod_name": {
                        "type": "string",
                        "description": "Pod name"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines to tail",
                        "default": 100
                    }
                },
                "required": ["environment", "namespace", "pod_name"]
            }
        ),
        
        Tool(
            name="k8s_list_contexts",
            description="List all available Kubernetes contexts/environments",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        
        Tool(
            name="k8s_get_nodes",
            description="Get nodes in specified environment cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": list(set(CONTEXTS.values())),
                        "description": "Target environment"
                    }
                },
                "required": ["environment"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Resolve environment to context
    env = arguments.get("environment")
    context = CONTEXTS.get(env, env) if env else None
    
    if name == "k8s_get_pods":
        args = ["get", "pods"]
        
        if arguments.get("namespace"):
            args.extend(["-n", arguments["namespace"]])
        else:
            args.append("--all-namespaces")
        
        if arguments.get("pod_name"):
            args.append(arguments["pod_name"])
        
        result = run_kubectl(args, context)
        
        if result["success"]:
            pods = result["data"].get("items", [])
            response = f"**Pods in {env} cluster:**\n\n"
            
            for pod in pods:
                name = pod["metadata"]["name"]
                namespace = pod["metadata"]["namespace"]
                status = pod["status"]["phase"]
                ready = "?"
                
                # Count ready containers
                if "containerStatuses" in pod["status"]:
                    containers = pod["status"]["containerStatuses"]
                    ready_count = sum(1 for c in containers if c.get("ready", False))
                    total_count = len(containers)
                    ready = f"{ready_count}/{total_count}"
                
                response += f"• {name} ({namespace}) - {status} - Ready: {ready}\n"
            
            if not pods:
                response += "No pods found.\n"
            
            return [TextContent(type="text", text=response)]
        else:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
    
    elif name == "k8s_get_deployments":
        args = ["get", "deployments"]
        
        if arguments.get("namespace"):
            args.extend(["-n", arguments["namespace"]])
        else:
            args.append("--all-namespaces")
        
        result = run_kubectl(args, context)
        
        if result["success"]:
            deployments = result["data"].get("items", [])
            response = f"**Deployments in {env} cluster:**\n\n"
            
            for dep in deployments:
                name = dep["metadata"]["name"]
                namespace = dep["metadata"]["namespace"]
                replicas = dep["spec"]["replicas"]
                available = dep["status"].get("availableReplicas", 0)
                ready = dep["status"].get("readyReplicas", 0)
                response += f"• {name} ({namespace}) - {ready}/{replicas} ready, {available} available\n"
            
            if not deployments:
                response += "No deployments found.\n"
            
            return [TextContent(type="text", text=response)]
        else:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
    
    elif name == "k8s_get_services":
        args = ["get", "services"]
        
        if arguments.get("namespace"):
            args.extend(["-n", arguments["namespace"]])
        else:
            args.append("--all-namespaces")
        
        result = run_kubectl(args, context)
        
        if result["success"]:
            services = result["data"].get("items", [])
            response = f"**Services in {env} cluster:**\n\n"
            
            for svc in services:
                name = svc["metadata"]["name"]
                namespace = svc["metadata"]["namespace"]
                svc_type = svc["spec"]["type"]
                cluster_ip = svc["spec"].get("clusterIP", "None")
                
                # Get external IP/hostname for LoadBalancer services
                external = ""
                if svc_type == "LoadBalancer":
                    ingress = svc["status"].get("loadBalancer", {}).get("ingress", [])
                    if ingress:
                        external_ip = ingress[0].get("ip", ingress[0].get("hostname", ""))
                        if external_ip:
                            external = f" - External: {external_ip}"
                
                response += f"• {name} ({namespace}) - {svc_type} - {cluster_ip}{external}\n"
            
            if not services:
                response += "No services found.\n"
            
            return [TextContent(type="text", text=response)]
        else:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
    
    elif name == "k8s_get_namespaces":
        result = run_kubectl(["get", "namespaces"], context)
        
        if result["success"]:
            namespaces = result["data"].get("items", [])
            response = f"**Namespaces in {env} cluster:**\n\n"
            
            for ns in namespaces:
                name = ns["metadata"]["name"]
                status = ns["status"]["phase"]
                response += f"• {name} - {status}\n"
            
            return [TextContent(type="text", text=response)]
        else:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
    
    elif name == "k8s_describe_pod":
        args = [
            "describe", "pod",
            arguments["pod_name"],
            "-n", arguments["namespace"]
        ]
        
        # For describe, don't use JSON output
        cmd = ["kubectl", "--context", context] + args
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return [TextContent(type="text", text=result.stdout)]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error: {e.stderr}")]
    
    elif name == "k8s_get_logs":
        args = [
            "logs",
            arguments["pod_name"],
            "-n", arguments["namespace"],
            f"--tail={arguments.get('tail', 100)}"
        ]
        
        cmd = ["kubectl", "--context", context] + args
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            log_output = result.stdout
            
            # Truncate if too long (MCP has limits)
            max_chars = 10000
            if len(log_output) > max_chars:
                log_output = log_output[-max_chars:] + "\n\n[... truncated to last 10000 characters]"
            
            return [TextContent(type="text", text=log_output)]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error: {e.stderr}")]
    
    elif name == "k8s_list_contexts":
        try:
            result = subprocess.run(
                ["kubectl", "config", "get-contexts", "-o", "name"],
                capture_output=True,
                text=True,
                check=True
            )
            
            contexts = result.stdout.strip().split("\n")
            response = "**Available Kubernetes Contexts:**\n\n"
            
            # Get current context
            current_ctx_result = subprocess.run(
                ["kubectl", "config", "current-context"],
                capture_output=True,
                text=True
            )
            current_ctx = current_ctx_result.stdout.strip()
            
            for ctx in contexts:
                marker = "→" if ctx == current_ctx else " "
                response += f"{marker} {ctx}\n"
            
            return [TextContent(type="text", text=response)]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error: {e.stderr}")]
    
    elif name == "k8s_get_nodes":
        result = run_kubectl(["get", "nodes"], context)
        
        if result["success"]:
            nodes = result["data"].get("items", [])
            response = f"**Nodes in {env} cluster:**\n\n"
            
            for node in nodes:
                name = node["metadata"]["name"]
                status = "Unknown"
                
                # Get node status
                conditions = node["status"].get("conditions", [])
                for condition in conditions:
                    if condition["type"] == "Ready":
                        status = "Ready" if condition["status"] == "True" else "NotReady"
                        break
                
                # Get node info
                node_info = node["status"].get("nodeInfo", {})
                kubelet_version = node_info.get("kubeletVersion", "unknown")
                
                # Get capacity
                capacity = node["status"].get("capacity", {})
                cpu = capacity.get("cpu", "?")
                memory = capacity.get("memory", "?")
                
                response += f"• {name}\n"
                response += f"  Status: {status}\n"
                response += f"  Version: {kubelet_version}\n"
                response += f"  Capacity: {cpu} CPU, {memory} memory\n\n"
            
            if not nodes:
                response += "No nodes found.\n"
            
            return [TextContent(type="text", text=response)]
        else:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


if __name__ == "__main__":
    import asyncio
    import mcp.server.stdio
    
    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    
    asyncio.run(main())