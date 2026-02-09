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
                        "enum": ["dev", "staging", "production", "qa", "uat"],
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
                        "description": "GitOps repository URL for Kubernetes manifests (e.g., https://github.com/allvest-wm/git-ops.git)"
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
                    "cronjobs": {
                        "type": "array",
                        "description": "Optional list of CronJob configurations",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "schedule": {"type": "string"},
                                "suspend": {"type": "boolean"},
                                "cmd": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["name"]
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
            Check the status of an ArgoCD application.
            Returns sync status, health status, and resource details.

            Use this to monitor applications deployed via ArgoCD.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "argocd_app_name": {
                        "type": "string",
                        "description": "ArgoCD application name (e.g., user-service-dev)"
                    }
                },
                "required": ["argocd_app_name"]
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
                        "enum": ["dev", "staging", "production", "qa", "uat"],
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
            List ArgoCD applications with optional filters.
            Shows application names, sync status, and health status.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Filter by ArgoCD project name (optional)"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Filter by source repository URL (optional)"
                    },
                    "sync_status": {
                        "type": "string",
                        "description": "Filter by sync status (optional)",
                        "enum": ["Synced", "OutOfSync", "Unknown"]
                    },
                    "health_status": {
                        "type": "string",
                        "description": "Filter by health status (optional)",
                        "enum": ["Healthy", "Degraded", "Progressing", "Suspended", "Missing", "Unknown"]
                    }
                }
            }
        ),
        
        Tool(
            name="cleanup_deployment",
            description="""
            Cleanup all resources created by a deploy_microservice operation.

            This will remove:
            - Cloudflare DNS records
            - ArgoCD applications
            - GitOps repository manifests
            - Microservice repository workflows
            - GitHub secrets (only if explicitly named)

            IMPORTANT: This is a destructive write operation.
            For production or force cleanup, an audit_comment is required.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "microservice_name": {
                        "type": "string",
                        "description": "Name of the microservice to cleanup"
                    },
                    "environment": {
                        "type": "string",
                        "enum": ["dev", "staging", "production", "qa", "uat"],
                        "description": "Target environment"
                    },
                    "domain_name": {
                        "type": "string",
                        "description": "Full domain name (e.g., app.dev.example.com)"
                    },
                    "argocd_app_name": {
                        "type": "string",
                        "description": "ArgoCD application name (e.g., user-service-dev)"
                    },
                    "gitops_repo_url": {
                        "type": "string",
                        "description": "GitOps repository URL"
                    },
                    "microservice_repo_url": {
                        "type": "string",
                        "description": "Microservice repository URL"
                    },
                    "github_secret_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Explicit list of GitHub secret names to delete (optional, opt-in only)"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Skip safety validations (requires audit_comment)",
                        "default": False
                    },
                    "audit_comment": {
                        "type": "string",
                        "description": "Reason for cleanup (required for production or force cleanup)",
                        "maxLength": 500
                    }
                },
                "required": [
                    "microservice_name",
                    "environment",
                    "domain_name",
                    "argocd_app_name",
                    "gitops_repo_url",
                    "microservice_repo_url"
                ]
            }
        ),

        Tool(
            name="rollback_deployment",
            description="""
            Rollback an ArgoCD application to a specific revision.

            This will trigger ArgoCD to sync the application to the specified
            revision and monitor rollback completion.

            IMPORTANT: This is a write operation that modifies production systems.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "argocd_app_name": {
                        "type": "string",
                        "description": "ArgoCD application name (e.g., user-service-dev)"
                    },
                    "revision": {
                        "type": "string",
                        "description": "Target revision to rollback to (commit SHA or tag)"
                    }
                },
                "required": ["argocd_app_name", "revision"]
            }
        ),

        Tool(
            name="quick_deploy_microservice",
            description="""
            Simplified deployment tool that requires only environment and GitHub URL.

            All other deployment parameters are automatically derived:
            - microservice_name: Extracted from GitHub URL
            - gitops_repo_url: Standard GitOps repository
            - git_branch: Same as environment
            - argocd_app_name: {microservice_name}-{environment}
            - domain_name: {microservice_name}-{environment}.allvestfinance.in
            - container_port: 3000 (default, can be overridden)

            This tool delegates to deploy_microservice internally, providing the same
            full deployment orchestration (manifests, GitOps, GitHub workflows, DNS, ArgoCD).

            Use this for standard deployments following organizational conventions.
            Use deploy_microservice directly when custom configuration is needed.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": ["dev", "staging", "production", "qa", "uat"],
                        "description": "Target deployment environment"
                    },
                    "microservice_github_url": {
                        "type": "string",
                        "description": "GitHub repository URL for the microservice (e.g., https://github.com/allvest-wm/user-service)"
                    },
                    "container_port": {
                        "type": "integer",
                        "description": "Container port number (optional, defaults to 3000)",
                        "minimum": 1,
                        "maximum": 65535,
                        "default": 3000
                    },
                    "env_content": {
                        "type": "string",
                        "description": "Environment variables in .env format (optional, KEY=VALUE pairs, one per line)"
                    }
                },
                "required": ["environment", "microservice_github_url"]
            }
        )
    ]