# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the DevOps Automation API - a FastAPI-based REST API that wraps ArgoCD operations and provides GitOps configuration management for microservices. It allows automated management of ArgoCD applications, projects, repositories, and clusters, plus GitOps-style ConfigMap updates and Kubernetes manifest generation.

## Development Commands

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn main:app --reload

# Run with specific host/port
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Configuration

The application uses `.env.development` or `.env.uat` files for configuration. Key settings:

- `ARGOCD_SERVER`: ArgoCD server URL (required)
- `ARGOCD_TOKEN` or `ARGOCD_USERNAME`/`ARGOCD_PASSWORD`: Authentication
- `VERIFY_SSL`: SSL certificate verification (default: true)
- `API_KEY`: Optional API key for securing endpoints (via `X-API-Key` header)
- `UPLOAD_DIR`: Directory for temporary file uploads and session storage
- `SESSION_EXPIRY_HOURS`: Hours before sessions expire
- `SESSION_CLEANUP_INTERVAL_HOURS`: Interval for cleaning expired sessions
- `CLOUDFLARE_API_TOKEN`: Cloudflare API token (for DNS operations)

## Architecture

### Layer Structure

```
main.py                     # FastAPI app initialization, middleware, exception handlers
app/
├── core/
│   ├── config.py          # Pydantic settings loaded from .env files
│   ├── dependencies.py    # FastAPI dependency injection (get_argocd_service, API key validation)
│   ├── exceptions.py      # Custom exception classes (ArgoCDException hierarchy)
│   ├── logging_config.py  # Logging setup
│   └── log_stream.py      # Streaming log handler for real-time SSE log output
├── routes/                # FastAPI routers
│   ├── argocd.py         # ArgoCD endpoints (/api/argocd/*)
│   ├── configmap.py      # GitOps ConfigMap endpoints (/api/configmap/*)
│   ├── gitops.py         # GitOps manifest generation endpoints (/api/gitops/*)
│   └── routes.py         # General API status endpoint
├── controllers/           # Request/response handling, validation
│   ├── argocd_controller.py
│   ├── configmap_controller.py
│   └── gitops_manifest_controller.py  # GitOps manifest generation controller
├── services/              # Business logic layer
│   ├── argocd_service.py  # High-level ArgoCD operations with auto token renewal
│   ├── configmap_service.py # ConfigMap/values.yaml file manipulation
│   ├── git_service.py     # Git clone, commit, push operations
│   ├── gitops_template_service.py  # Template processing with variable substitution
│   ├── cloudflare_service.py  # Cloudflare DNS API operations
│   ├── session_manager.py  # Session creation, storage, and cleanup
│   └── file_handler.py    # File handling utilities
├── models/                # Pydantic models
│   ├── argocd.py         # Request/response models for ArgoCD
│   ├── configmap.py      # ConfigMap update models
│   ├── gitops.py         # GitOps manifest request/response models
│   ├── schemas.py        # Pydantic schemas for config changes (preview/apply workflow)
│   └── common.py         # Shared models (BaseResponse, enums)
├── utils/
│   ├── argocd_client.py  # Low-level ArgoCD REST API client
│   ├── helpers.py        # Utility functions for building API specs
│   └── cleanup.py        # Session cleanup utilities
└── templates/            # Helm chart and GitHub workflow templates
    ├── git-ops/          # Kubernetes/Helm manifest templates
    └── github/           # GitHub Actions workflow templates
```

### Request Flow

1. Routes define FastAPI endpoints and inject dependencies
2. Controllers handle request validation and response formatting
3. Services contain business logic and orchestration
4. `ArgoCDClient` (utils) makes actual HTTP calls to ArgoCD API

### Key Patterns

**Dependency Injection**: The `get_argocd_service` function in `app/core/dependencies.py` creates an `ArgoCDService` instance per request, configured from environment settings.

**Auto Token Renewal**: `ArgoCDService._execute_with_retry()` automatically renews expired ArgoCD tokens when username/password are available.

**ConfigMap Update Workflow**: The `/api/configmap/update` endpoint clones a GitOps repo, updates `values.yaml` and `configmap.yaml` files, commits, pushes, and optionally syncs ArgoCD.

**GitOps Manifest Generation**: The `/api/gitops/micro-service` endpoint processes template files with variable substitution and returns a streaming response with real-time logs.

**Streaming Logs**: The `LogStreamHandler` in `log_stream.py` uses context variables to stream logs to specific requests via Server-Sent Events (NDJSON format).

**Session Management**: `SessionManager` handles preview/apply workflows by storing session state both in memory and on disk for persistence.

## API Documentation

When running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Key Endpoints

- `GET /health` - Health check
- `GET /api/argocd/applications` - List ArgoCD applications
- `POST /api/argocd/applications/{name}/sync` - Sync an application
- `POST /api/configmap/update` - Complete GitOps config update workflow
- `POST /api/configmap/preview` - Preview changes without applying
- `POST /api/gitops/micro-service` - Generate Kubernetes manifests from templates (streaming response)

## Template Variables

The GitOps template service supports these placeholders:

- `{{MICRO_SERVICE_NAME}}` - Microservice name
- `{{MICRO_SERVICE_URL}}` - Microservice URL/path
- `{{CONTAINER_PORT}}` - Container port
- `{{DOMAIN_NAME}}` - Domain name for ingress
- `{{ENVIRONMENT}}` - Target environment
- `{{GIT_REPO_NAME}}` - Git repository name
- `{{GIT_BRANCH}}` - Git branch
- `{{GIT_SECRET}}` - GitHub secret key
- `{{ARGOCD_APP_NAME}}` - ArgoCD application name
- `{{GITOPS_REPO_URL}}` - GitOps repository URL
- `{{ENVIRONMENT_VARIABLES}}` - Parsed env vars (YAML format)
- `{{CRONJOB_YAML}}` - CronJob configuration block
