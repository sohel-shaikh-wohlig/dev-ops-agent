"""
Deployment tool definitions
Separated from implementation for clean architecture
"""

from mcp.types import Tool


def get_deployment_tools() -> list[Tool]:
    """
    Get all deployment tool definitions
    
    Returns:
        List of Tool objects for MCP server
    """
    return [
        Tool(
            name="deploy_microservice",
            description="""
            Deploy a microservice to GKE cluster with complete end-to-end automation.
            
            This tool orchestrates the entire deployment process:
            1. Generates Kubernetes manifests from templates
            2. Clones GitOps repository and commits manifests
            3. Clones microservice repository and adds GitHub workflows
            4. Creates GitHub repository secrets
            5. Creates Cloudflare DNS record
            6. Monitors GitHub Action workflow completion
            7. Creates and syncs ArgoCD application
            
            The deployment happens across multiple systems (GitHub, Kubernetes, ArgoCD, Cloudflare)
            and includes automatic rollback on failure.
            
            IMPORTANT: This is a write operation that will:
            - Modify GitHub repositories (commits & pushes)
            - Create DNS records in Cloudflare
            - Deploy applications to Kubernetes cluster
            
            Use GitHub MCP to verify repository exists before deploying.
            Use Kubernetes MCP to check cluster health before deploying.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": ["development", "staging", "production", "qa", "uat"],
                        "description": "Target deployment environment"
                    },
                    "microservice_name": {
                        "type": "string",
                        "description": "Name of the microservice to deploy",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "microservice_url": {
                        "type": "string",
                        "description": "GitHub repository URL for the microservice (e.g., https://github.com/org/service.git)"
                    },
                    "container_port": {
                        "type": "integer",
                        "description": "Container port number (1-65535)",
                        "minimum": 1,
                        "maximum": 65535
                    },
                    "gitops_repo_url": {
                        "type": "string",
                        "description": "GitOps repository URL for Kubernetes manifests"
                    },
                    "git_repo_name": {
                        "type": "string",
                        "description": "Git repository name",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "git_branch": {
                        "type": "string",
                        "description": "Git branch name",
                        "default": "main"
                    },
                    "argocd_app_name": {
                        "type": "string",
                        "description": "ArgoCD application name (e.g., user-service-dev)",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "domain_name": {
                        "type": "string",
                        "description": "Domain name for ingress (e.g., api.example.com)"
                    },
                    "env_content": {
                        "type": "string",
                        "description": "Environment variables in .env format (KEY=VALUE pairs, one per line)"
                    },
                    "cronjob": {
                        "type": "object",
                        "description": "Optional CronJob configuration",
                        "properties": {
                            "name": {"type": "string"},
                            "schedule": {"type": "string"},
                            "suspend": {"type": "boolean"},
                            "cmd": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                },
                "required": [
                    "environment",
                    "microservice_name",
                    "microservice_url",
                    "container_port",
                    "gitops_repo_url",
                    "git_repo_name",
                    "argocd_app_name",
                    "domain_name"
                ]
            }
        ),
        
        Tool(
            name="check_deployment_status",
            description="""
            Check the real-time status of an ongoing or completed deployment.
            Returns current step, progress, and any errors.
            
            This is useful for monitoring deployments initiated by deploy_microservice.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "microservice_name": {
                        "type": "string",
                        "description": "Name of the microservice to check"
                    },
                    "environment": {
                        "type": "string",
                        "enum": ["development", "staging", "production", "qa", "uat"],
                        "description": "Environment to check"
                    }
                },
                "required": ["microservice_name", "environment"]
            }
        ),
        
        Tool(
            name="get_deployment_plan",
            description="""
            Get a detailed deployment plan without executing it (dry-run).
            Shows what will happen step-by-step for review before deployment.
            
            Use this before deploy_microservice to validate configuration.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "microservice_name": {
                        "type": "string",
                        "description": "Microservice name"
                    },
                    "environment": {
                        "type": "string",
                        "enum": ["development", "staging", "production", "qa", "uat"],
                        "description": "Target environment"
                    },
                    "microservice_url": {
                        "type": "string",
                        "description": "Microservice repository URL"
                    },
                    "gitops_repo_url": {
                        "type": "string",
                        "description": "GitOps repository URL"
                    }
                },
                "required": ["microservice_name", "environment", "microservice_url", "gitops_repo_url"]
            }
        ),
        
        Tool(
            name="list_recent_deployments",
            description="""
            List recent deployments across all environments.
            Shows deployment history, status, and timestamps.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent deployments to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "environment": {
                        "type": "string",
                        "description": "Filter by environment (optional)",
                        "enum": ["development", "staging", "production", "qa", "uat"]
                    }
                }
            }
        ),
        
        Tool(
            name="rollback_deployment",
            description="""
            Rollback a deployment to the previous version.
            
            This will:
            1. Revert GitOps repository to previous commit
            2. Trigger ArgoCD sync
            3. Monitor rollback completion
            
            IMPORTANT: This is a write operation that modifies production systems.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "microservice_name": {
                        "type": "string",
                        "description": "Name of the microservice to rollback"
                    },
                    "environment": {
                        "type": "string",
                        "enum": ["development", "staging", "production", "qa", "uat"],
                        "description": "Environment to rollback"
                    }
                },
                "required": ["microservice_name", "environment"]
            }
        )
    ]