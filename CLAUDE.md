# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DevOps Automation Platform for managing microservice deployments via ArgoCD, GitOps, Kubernetes, GitHub, and Cloudflare. Three main components:

- **api/** - FastAPI backend REST API (see `api/CLAUDE.md` for details)
- **frontend/** - React + TypeScript web dashboard (see `frontend/CLAUDE.md` for details)
- **devops_mcp/** - MCP (Model Context Protocol) servers for Claude Desktop integration

## Development Commands

### Backend (FastAPI)
```bash
cd api
source venv/bin/activate  # or: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev      # Start Vite dev server at http://localhost:5173
npm run build    # TypeScript check + production build
npm run lint     # ESLint check
```

### MCP Servers
```bash
# Test standalone
python devops_mcp/servers/devops_automation.py

# Test with inspector (interactive web UI)
mcp-inspector python devops_mcp/servers/devops_automation.py

# For Claude Desktop: configure ~/Library/Application Support/Claude/claude_desktop_config.json
```

## Architecture

### Data Flow
```
Claude Desktop / Web UI
         │
         ▼
   MCP Servers (devops_mcp/)  ───── JSON-RPC over stdio
         │
         ▼ HTTP/JSON
   FastAPI Backend (api/)
         │
         ├── ArgoCD API
         ├── GitHub API
         ├── Cloudflare API
         └── Git operations
```

### Backend Layers (api/)
- **routes/** - FastAPI endpoint definitions
- **controllers/** - Request validation and response formatting
- **services/** - Business logic (ArgoCD, Git, Cloudflare, session management)
- **models/** - Pydantic request/response schemas
- **utils/** - Low-level HTTP clients
- **templates/** - Helm charts and GitHub Actions workflow templates

### MCP Integration (devops_mcp/)
- **servers/devops_automation.py** - Main deployment orchestration server
- **servers/kubernetes_multi.py** - Multi-cluster Kubernetes operations
- **shared/api_client.py** - Async HTTP client for FastAPI backend
- **config/settings.py** - Environment configuration via pydantic-settings

### Frontend Structure (frontend/)
Feature-based organization: `features/{argocd,configmap,gitops,github-deploy}/`
Each feature contains components/, services/, types/, and barrel exports.

## Environment Configuration

Create `.env` files (gitignored) with:
```bash
# Backend
ARGOCD_SERVER=https://argocd.example.com
ARGOCD_TOKEN=xxx  # or ARGOCD_USERNAME/ARGOCD_PASSWORD
GITHUB_TOKEN=xxx
CLOUDFLARE_API_TOKEN=xxx

# MCP
MCP_FASTAPI_URL=http://localhost:8000
MCP_LOG_LEVEL=INFO
```

Multi-environment support: `ARGOCD_SERVER_DEV`, `ARGOCD_SERVER_UAT`, `ARGOCD_SERVER_STAGING`, `ARGOCD_SERVER_PROD`

## Key Patterns

**Auto Token Renewal**: `ArgoCDService._execute_with_retry()` automatically renews expired ArgoCD tokens.

**Streaming Logs**: GitOps operations stream real-time logs via SSE (NDJSON format) using `LogStreamHandler`.

**Session Management**: Preview/apply workflows store state in memory and disk for persistence across requests.

**MCP Protocol**: Servers communicate via JSON-RPC over stdio. Use mcp-inspector for development testing.

## API Endpoints

- `GET /health` - Health check
- `GET /api/argocd/applications` - List ArgoCD apps
- `POST /api/argocd/applications/{name}/sync` - Sync application
- `POST /api/gitops/micro-service` - Generate K8s manifests (streaming)
- `POST /api/configmap/update` - GitOps config update workflow

## MCP Tools

- `deploy_microservice` - Full deployment orchestration
- `check_deployment_status` - ArgoCD app status
- `get_deployment_plan` - Dry-run preview
- `list_recent_deployments` - List ArgoCD apps with filters
- `cleanup_deployment` - Resource cleanup with audit trail
- `rollback_deployment` - Rollback to specific revision

See `devops_mcp/PROMPTS.md` for example Claude prompts.
