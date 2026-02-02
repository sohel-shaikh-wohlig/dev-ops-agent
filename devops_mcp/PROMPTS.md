# DevOps MCP - Claude Desktop Prompt Examples

Example prompts for triggering MCP tools via Claude Desktop.

## deploy_microservice

### Basic Deployment

```
Deploy poc-star microservice to dev environment.
- Microservice repo: https://github.com/allvest-wm/poc-star
- Container port: 3000
- GitOps repo: https://github.com/allvest-wm/git-ops
- Git repo name: poc-star
- Git branch: dev
- ArgoCD app: poc-star-dev
- Domain: poc-star-dev.allvestfinance.in
```

### Deployment with Environment Variables

```
Deploy user-service to staging.
- Microservice repo: https://github.com/allvest-wm/user-service
- Container port: 8080
- GitOps repo: https://github.com/allvest-wm/git-ops
- Git repo name: user-service
- Git branch: staging
- ArgoCD app: user-service-staging
- Domain: user-service-staging.allvestfinance.in
- Env vars:
  NODE_ENV=staging
  DATABASE_URL=postgresql://db:5432/users
  LOG_LEVEL=debug
```

### Deployment with CronJobs

```
Deploy data-processor to dev with a daily sync cronjob.
- Microservice repo: https://github.com/allvest-wm/data-processor
- Container port: 3000
- GitOps repo: https://github.com/allvest-wm/git-ops
- Git repo name: data-processor
- Git branch: dev
- ArgoCD app: data-processor-dev
- Domain: data-processor-dev.allvestfinance.in
- Cronjob: name=data-sync, schedule="0 2 * * *", command=["npm", "run", "sync"]
```

## cleanup_deployment

### Basic Cleanup

```
Clean up the poc-star microservice from the dev environment.
- Domain: poc-star-dev.allvestfinance.in
- ArgoCD app: poc-star-dev
- GitOps repo: https://github.com/allvest-wm/git-ops
- Microservice repo: https://github.com/allvest-wm/poc-star
```

### Cleanup with GitHub Secrets

```
Remove the poc-star deployment from dev including GitHub secrets DOCKER_USER and GCP_SA_KEY.
- Domain: poc-star-dev.allvestfinance.in
- ArgoCD app: poc-star-dev
- GitOps repo: https://github.com/allvest-wm/git-ops
- Microservice repo: https://github.com/allvest-wm/poc-star
```

### Force Cleanup (Production)

```
Force cleanup poc-star from production. Audit reason: "Decommissioning service after migration to v2."
- Domain: poc-star.allvestfinance.in
- ArgoCD app: poc-star-prod
- GitOps repo: https://github.com/allvest-wm/git-ops
- Microservice repo: https://github.com/allvest-wm/poc-star
```

## check_deployment_status

```
Check the status of the poc-star-dev ArgoCD application.
```

## list_recent_deployments

```
List all ArgoCD applications.
```

```
Show me all unhealthy ArgoCD applications.
```

```
List ArgoCD applications in the dev project that are out of sync.
```

## rollback_deployment

```
Rollback poc-star-dev to revision abc123def.
```

## get_deployment_plan

```
Show me the deployment plan for poc-star to dev.
- Microservice repo: https://github.com/allvest-wm/poc-star
- GitOps repo: https://github.com/allvest-wm/git-ops
```
