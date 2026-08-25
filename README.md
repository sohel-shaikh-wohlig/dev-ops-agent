# DevOps Automation Platform

Manages microservice deployments across ArgoCD, GitOps, Kubernetes, GitHub, and Cloudflare.
See [CLAUDE.md](CLAUDE.md) for development commands, architecture notes, and environment configuration.

## Folder Structure

```
dev-ops-automation/
├── api/                                    # FastAPI backend (see api/CLAUDE.md)
│   ├── app/
│   │   ├── client_config/                  # Per-client YAML config (acme, vaultfy)
│   │   ├── controllers/                    # Request validation / response formatting
│   │   │   ├── argocd_controller.py
│   │   │   ├── configmap_controller.py
│   │   │   ├── github_webhook_controller.py
│   │   │   ├── gitops_manifest_controller.py
│   │   │   └── terraform_controller.py
│   │   ├── core/                           # Config, DI, logging, redis, pubsub, websockets
│   │   ├── models/                         # Pydantic request/response schemas
│   │   ├── repositories/                   # Data access layer
│   │   ├── routes/                         # FastAPI endpoint definitions
│   │   ├── services/                       # Business logic
│   │   │   ├── argocd_service.py
│   │   │   ├── git_service.py
│   │   │   ├── gitops_template_service.py
│   │   │   ├── cloudflare_service.py
│   │   │   ├── github_webhook_service.py
│   │   │   ├── deployment_service.py
│   │   │   ├── session_manager.py
│   │   │   └── ...
│   │   ├── templates/                      # Helm charts, GitHub Actions, Terraform
│   │   │   ├── git-ops/
│   │   │   ├── github/
│   │   │   └── terraform/
│   │   └── utils/                          # Low-level clients (argocd_client, gh_cli, ...)
│   │
│   ├── main.py                             # FastAPI app entry point
│   ├── requirements.txt                    # Backend dependencies
│   ├── start.sh                            # Local run script
│   └── .env.example
│
├── devops_mcp/                             # MCP servers for Claude Desktop
│   ├── __init__.py
│   ├── servers/                            # MCP server implementations
│   │   ├── __init__.py
│   │   ├── devops_automation.py            # Deployment orchestration MCP
│   │   └── kubernetes_multi.py             # Multi-cluster K8s MCP
│   │
│   ├── shared/                             # Shared MCP utilities
│   │   ├── __init__.py
│   │   ├── base_server.py                  # Base MCP server class
│   │   ├── api_client.py                   # FastAPI client wrapper
│   │   └── logging.py                      # MCP-specific logging
│   │
│   ├── config/                             # MCP configuration
│   │   ├── __init__.py
│   │   ├── settings.py                     # MCP settings (URLs, tokens, etc.)
│   │   └── contexts.py                     # Kubernetes context mappings
│   │
│   ├── tools/                              # Tool definitions (schemas)
│   │   ├── __init__.py
│   │   └── deployment_tools.py
│   │
│   ├── requirements-mcp.txt                # MCP dependencies
│   ├── PROMPTS.md                          # Example Claude prompts
│   └── README.md
│
├── frontend/                               # React + TypeScript dashboard
│   ├── src/
│   │   ├── features/                       # Feature-based modules
│   │   │   ├── argocd/
│   │   │   ├── configmap/
│   │   │   ├── dashboard/
│   │   │   ├── github-deploy/
│   │   │   ├── gitops/
│   │   │   └── terraform/
│   │   ├── components/                     # Shared UI components
│   │   ├── shared/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── assets/
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── .env.example
│
├── scripts/                                # Management scripts
│   ├── setup/
│   │   └── setup_multi_cluster_k8s.sh      # K8s cluster setup
│   └── maintenance/
│       └── health_check.py                 # MCP health check
│
├── docs/                                   # Documentation
│   ├── api/
│   │   └── websoket_implementation_plan.md
│   └── mcp/
│       └── README.md                       # MCP overview
│
├── logs/                                   # Runtime logs (gitignored)
│   └── mcp/
│
├── docker-compose.yml
├── PLAN-gh-cli-migration.md                # GitHub CLI migration plan
├── CLAUDE.md                               # Guidance for Claude Code
├── .gitignore
└── README.md
```
