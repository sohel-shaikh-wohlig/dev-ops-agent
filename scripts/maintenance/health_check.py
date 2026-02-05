# scripts/maintenance/health_check.py

"""
MCP Health Check Script
Verifies all MCP servers are functioning
"""

import subprocess
import sys

def check_mcp_server(server_path: str) -> bool:
    """Check if MCP server is working"""
    try:
        result = subprocess.run(
            ["python", server_path, "--check"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking {server_path}: {e}")
        return False

if __name__ == "__main__":
    servers = [
        "devops_mcp/servers/devops_automation.py",
        "devops_mcp/servers/kubernetes_multi.py"
    ]
    
    all_healthy = True
    for server in servers:
        if check_mcp_server(server):
            print(f"✓ {server} is healthy")
        else:
            print(f"✗ {server} failed health check")
            all_healthy = False
    
    sys.exit(0 if all_healthy else 1)