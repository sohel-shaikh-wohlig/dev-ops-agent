### Recommended Folder Structure
dev-ops-automation/
├── api/                                    # Your existing API
│   ├── apps/
│   │   ├── controller/                     # Existing controllers
│   │   ├── routes/                         # Existing routes
│   |   ├── models/                         # Pydantic models
│   │   └── services/                       # Existing services
│   │       ├── gitops_service.py           # Your deployment logic
│   │       ├── argocd_service.py
│   │       ├── github_service.py
│   │       └── cloudflare_service.py
|   |
│   ├── config/                             # FastAPI configuration
│   └── main.py                             # FastAPI app entry point
│
├── mcp/                                    # MCP Integration (NEW)
│   ├── __init__.py
│   ├── servers/                            # MCP server implementations
│   │   ├── __init__.py
│   │   ├── devops_automation.py            # Your custom deployment MCP
│   │   ├── kubernetes_multi.py             # Multi-cluster K8s MCP
│   │   └── token_provider.py               # Token management MCP (optional)
│   │
│   ├── shared/                             # Shared MCP utilities
│   │   ├── __init__.py
│   │   ├── base_server.py                  # Base MCP server class
│   │   ├── api_client.py                   # FastAPI client wrapper
│   │   └── logging.py                      # MCP-specific logging
│   │
│   ├── config/                             # MCP configurations
│   │   ├── __init__.py
│   │   ├── settings.py                     # MCP settings (URLs, tokens, etc.)
│   │   └── contexts.py                     # Kubernetes context mappings
│   │
│   └── tools/                              # Tool definitions (schemas)
│       ├── __init__.py
│       ├── deployment_tools.py             # Deployment tool schemas
│       └── kubernetes_tools.py             # K8s tool schemas
|
|
|── frontend
│   └── src/
│
├── scripts/                                # Management scripts
│   ├── setup/
│   │   ├── setup_mcp.sh                    # Initial MCP setup
│   │   ├── setup_multi_cluster_k8s.sh      # K8s cluster setup
│   │   └── create_user.py                  # Create auth users
│   │
│   ├── maintenance/
│   │   ├── refresh_tokens.py               # Token refresh script
│   │   ├── sync_clusters.py                # Sync K8s cluster configs
│   │   └── health_check.py                 # MCP health check
│   │
│   └── deployment/
│       ├── deploy_mcp_servers.sh           # Deploy MCP to production
│       └── rollback_mcp.sh                 # Rollback MCP changes
│
├── config/                                 # Project-wide configuration
│   ├── claude_desktop/
│   │   ├── config.dev.json                 # Development config
│   │   ├── config.staging.json             # Staging config
│   │   └── config.production.json          # Production config
│   │
│   ├── kubernetes/
│   │   ├── contexts.yaml                   # K8s context definitions
│   │   └── cluster_mappings.yaml           # Environment → cluster mapping
│   │
│   └── environments/
│       ├── .env.development
│       ├── .env.staging
│       └── .env.production
│
├── docs/                                   # Documentation
│   ├── mcp/
│   │   ├── README.md                       # MCP overview
│   │   ├── setup.md                        # Setup instructions
│   │   ├── tools.md                        # Tool documentation
│   │   └── examples.md                     # Usage examples
│   │
│   └── api/
│       └── ... (existing API docs)
│
├── tests/                                  # Tests
│   ├── api/                                # Existing API tests
│   │   └── ...
│   │
│   └── mcp/                                # MCP tests
│       ├── __init__.py
│       ├── test_devops_mcp.py              # Test deployment MCP
│       ├── test_kubernetes_mcp.py          # Test K8s MCP
│       └── fixtures/                       # Test fixtures
│           ├── mock_deployments.json
│           └── mock_clusters.json
│
├── logs/                                   # Logs directory
│   ├── api/                                # FastAPI logs
│   ├── mcp/                                # MCP server logs
│   │   ├── devops_automation.log
│   │   └── kubernetes_multi.log
│   └── scripts/                            # Script logs
│       └── token_refresh.log
│
|
├── .gitignore
├── requirements.txt                        # FastAPI dependencies
├── requirements-mcp.txt                    # MCP-specific dependencies
├── pyproject.toml                          # Project metadata
└── README.md                               # Main project README

Changed...
