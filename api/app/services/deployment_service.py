# app/services/deployment_service.py
"""
Deployment Service
Orchestrates the deployment of microservices across multiple services
"""

import asyncio
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple
import httpx

from app.core.logging_config import logger
from app.core.config import get_settings
from app.core.exceptions import ArgoCDAPIException
from app.services.gitops_template_service import GitOpsTemplateService
from app.services.configmap_service import ConfigMapService
from app.services.git_service import git_service
from app.services.argocd_service import ArgoCDService
from app.services.cloudflare_service import CloudflareService
from app.models.gitops import (
    GitOpsManifestRequest,
    GitOpsManifestResponse,
    ProcessedFile
)

settings = get_settings()


def _get_head_commit_hash(repo_dir: Path) -> Optional[str]:
    """Return the current HEAD commit hash for *repo_dir*, or None on failure."""
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_dir, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception as exc:
        logger.warning(f"Could not read HEAD commit hash from {repo_dir}: {exc}")
        return None


# Constants
HEALTH_POLL_INTERVAL = 10  # seconds between health checks
HEALTH_POLL_TIMEOUT = 300  # 5 minutes max wait time
WORKFLOW_POLL_INTERVAL = 10  # seconds between workflow status checks
WORKFLOW_POLL_MAX_ATTEMPTS = 60  # Max 10 minutes (60 * 10 seconds)
WORKFLOW_FETCH_MAX_RETRIES = 10
WORKFLOW_FETCH_RETRY_DELAY = 10  # seconds

# Environment variable validation patterns
ENV_VAR_PATTERNS = [
    # Python patterns
    (r"os\.environ\[(['\"])(\w+)\1\]", 2),                    # os.environ['VAR'] or os.environ["VAR"]
    (r"os\.getenv\((['\"])(\w+)\1", 2),                       # os.getenv('VAR') or os.getenv("VAR")
    (r"os\.environ\.get\((['\"])(\w+)\1", 2),                 # os.environ.get('VAR')
    # Node.js patterns
    (r"process\.env\.([A-Z][A-Z0-9_]*)", 1),                  # process.env.VAR_NAME
    # Shell/Docker patterns (be careful with false positives)
    (r"\$\{([A-Z][A-Z0-9_]*)\}", 1),                          # ${VAR_NAME}
    (r"(?<!\$)\$([A-Z][A-Z0-9_]*)\b", 1),                     # $VAR_NAME (not preceded by $)
]

# File extensions to scan for environment variables
SCANNABLE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs',
    '.sh', '.bash', '.zsh',
    '.yaml', '.yml',
    '.json', '.env.example', '.env.sample'
}

# Files to scan regardless of extension
SCANNABLE_FILES = {
    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    'docker-compose.dev.yml', 'docker-compose.prod.yml',
    '.env.example', '.env.sample', '.env.template'
}

# Directories to exclude from scanning
EXCLUDED_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv',
    'env', '.env', 'dist', 'build', '.next', '.nuxt',
    'coverage', '.pytest_cache', '.mypy_cache', '.tox',
    'vendor', 'packages', '.github'
}

# System/CI variables to exclude (false positives)
EXCLUDED_VARIABLES = {
    # System variables
    'PATH', 'HOME', 'USER', 'PWD', 'SHELL', 'TERM', 'LANG',
    'LC_ALL', 'LC_CTYPE', 'HOSTNAME', 'OLDPWD', 'SHLVL',
    'LOGNAME', 'MAIL', 'EDITOR', 'VISUAL', 'PAGER', 'LESS',
    'TZ', 'TMPDIR', 'TEMP', 'TMP',
    # Node.js built-ins
    'NODE_ENV', 'NODE_PATH', 'NODE_OPTIONS', 'NPM_CONFIG_PREFIX',
    'NODE_VERSION', 'NPM_VERSION', 'YARN_VERSION',
    # Python built-ins
    'PYTHONPATH', 'PYTHONHOME', 'PYTHONDONTWRITEBYTECODE',
    'PYTHONUNBUFFERED', 'VIRTUAL_ENV', 'PIP_CACHE_DIR',
    # CI/CD variables
    'CI', 'GITHUB_ACTIONS', 'GITHUB_ACTOR', 'GITHUB_REF',
    'GITHUB_SHA', 'GITHUB_REPOSITORY', 'GITHUB_RUN_ID',
    'GITHUB_RUN_NUMBER', 'GITHUB_WORKFLOW', 'GITHUB_HEAD_REF',
    'GITHUB_BASE_REF', 'GITHUB_EVENT_NAME', 'GITHUB_SERVER_URL',
    'GITHUB_API_URL', 'GITHUB_GRAPHQL_URL', 'GITHUB_WORKSPACE',
    'GITHUB_TOKEN', 'ACTIONS_RUNNER_DEBUG', 'ACTIONS_STEP_DEBUG',
    'RUNNER_OS', 'RUNNER_ARCH', 'RUNNER_NAME', 'RUNNER_TEMP',
    'RUNNER_TOOL_CACHE', 'RUNNER_WORKSPACE',
    # Docker variables
    'DOCKER_HOST', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH',
    'COMPOSE_PROJECT_NAME', 'COMPOSE_FILE',
    # Common optional/default variables
    'DEBUG', 'VERBOSE', 'LOG_LEVEL', 'PORT', 'HOST',
}


class DeploymentService:
    """Service for deploying microservices via GitOps workflow"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.template_service = GitOpsTemplateService()

    async def deploy(
        self,
        request: GitOpsManifestRequest,
        argocd_service: ArgoCDService
    ) -> GitOpsManifestResponse:
        """
        Deploy a microservice via GitOps workflow.

        Performs the following steps:
        0. Validate environment variables against microservice codebase
        1. Process templates with variable substitution
        2. Locate and validate microservice structure
        3. Parse and apply environment variables
        4. Clone GitOps repository and push manifests
        5. Create GitHub repository secrets
        6. Clone microservice repo and push GitHub workflows
        7. Create Cloudflare DNS record
        8. Monitor GitHub Action workflow
        9. Create and sync ArgoCD application

        Args:
            request: GitOps manifest generation request
            argocd_service: ArgoCD service instance

        Returns:
            GitOpsManifestResponse with processing results
        """
        logger.info("=" * 60)
        logger.info("STARTING DEPLOYMENT")
        logger.info(f"Microservice: {request.microservice_name}")
        logger.info(f"Environment: {request.environment}")
        logger.info("=" * 60)
        await asyncio.sleep(0)

        env_value = self._get_env_value(request)

        try:
            # Step 0: Validate environment variables
            await self._validate_env_variables(request, env_value)

            # Step 1: Process templates
            result = await self._process_templates(request, env_value)
            processed_files = self._build_processed_files(result)

            # Step 2: Locate and validate microservice
            gitops_path = await self._locate_microservice(request)

            # Step 3: Initialize and validate config service
            config_service = await self._init_config_service(gitops_path)

            # Step 4 & 5: Parse and apply environment variables
            await self._apply_env_variables(request, config_service)

            # Step 6: Clone GitOps repo and push manifests
            clone_repo_dir = await self._push_gitops_manifests(request, env_value)

            # Step 7: Create GitHub repository secrets
            await self._create_github_secrets(request)

            # Step 8 & 9: Clone microservice repo and push workflows
            workflow_commit_hash = await self._push_github_workflows(request, env_value)

            # Step 10: Cleanup temp folder
            await self._cleanup_temp_folder()

            # Step 11: Create Cloudflare DNS record
            await self._create_dns_record(request, env_value)

            # Step 12: Monitor GitHub Action and deploy via ArgoCD
            await self._monitor_and_deploy(
                request, argocd_service, env_value, workflow_commit_hash
            )

            # Build response
            response = GitOpsManifestResponse(
                status="success",
                message=f"{request.domain_name} deployed successfully",
                microservice_name=request.microservice_name,
                environment=env_value,
                output_directory=result['output_directory'],
                processed_files=processed_files,
                total_files_processed=result['total_files_processed'],
                template_variables=result['template_variables'],
                environment_variables=result.get('environment_variables', {}),
                cronjobs=result.get('cronjobs'),
                worker=result.get('worker')
            )

            logger.info("=" * 60)
            logger.info("DEPLOYMENT COMPLETE")
            logger.info(f"Output directory: {result['output_directory']}")
            logger.info(f"Files processed: {result['total_files_processed']}")
            logger.info("=" * 60)

            return response

        except ArgoCDAPIException as e:
            logger.error(f"ArgoCD API error: {str(e)}")
            logger.error(f"ArgoCD status code: {e.status_code}")
            logger.error(f"ArgoCD response: {e.response_text}")
            raise
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}", exc_info=True)
            raise

    def _get_env_value(self, request: GitOpsManifestRequest) -> str:
        """Extract environment value as string from request"""
        return request.environment.value if hasattr(request.environment, 'value') else str(request.environment)

    async def _validate_env_variables(
        self,
        request: GitOpsManifestRequest,
        env_value: str
    ) -> None:
        """
        Step 0: Validate environment variables against microservice codebase.

        Clones the microservice repository, scans for environment variable
        references, and validates against provided env_content.

        Args:
            request: GitOps manifest generation request
            env_value: Environment string (dev, uat, prod, etc.)

        Raises:
            Exception: If required environment variables are missing
        """
        logger.info("[Step 0] Validating environment variables...")
        await asyncio.sleep(0)

        # Create temp directory for validation
        validation_session_id = f"validation_{uuid.uuid4().hex[:8]}"
        validation_temp_dir = self.project_root / "app" / "temp" / validation_session_id
        validation_temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Clone microservice repository
            logger.info(f"Cloning microservice repository for validation...")
            clone_dir = validation_temp_dir / "repo"

            success, error = await asyncio.to_thread(
                git_service.clone_repository,
                request.microservice_url,
                clone_dir,
                branch=env_value
            )

            if not success:
                # Try main branch as fallback
                logger.warning(f"Failed to clone {env_value} branch, trying main...")
                success, error = await asyncio.to_thread(
                    git_service.clone_repository,
                    request.microservice_url,
                    clone_dir,
                    branch="main"
                )
                if not success:
                    raise Exception(f"Failed to clone repository for validation: {error}")

            logger.info(f"✓ Repository cloned for validation")

            # Scan repository for environment variable references
            logger.info("Scanning codebase for environment variable references...")
            required_vars = self._scan_for_env_variables(clone_dir)
            logger.info(f"Found {len(required_vars)} unique environment variable references")

            # Parse provided env_content
            provided_vars = self._parse_env_content_variables(request.env_content)
            logger.info(f"Provided {len(provided_vars)} environment variables in env_content")

            # Find missing variables
            missing_vars = {}
            for var_name, locations in required_vars.items():
                if var_name not in provided_vars:
                    missing_vars[var_name] = locations

            if missing_vars:
                error_msg = self._build_missing_vars_error(missing_vars)
                logger.error(error_msg)
                raise Exception(error_msg)

            logger.info("✓ All required environment variables are provided")

        finally:
            # Cleanup validation temp directory
            if validation_temp_dir.exists():
                shutil.rmtree(validation_temp_dir, ignore_errors=True)
                logger.debug(f"Cleaned up validation temp directory")

    def _scan_for_env_variables(self, repo_dir: Path) -> Dict[str, List[str]]:
        """
        Scan repository for environment variable references.

        Args:
            repo_dir: Path to the cloned repository

        Returns:
            Dictionary mapping variable names to list of file:line locations
        """
        env_vars: Dict[str, List[str]] = {}

        for file_path in self._get_scannable_files(repo_dir):
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                relative_path = file_path.relative_to(repo_dir)

                for line_num, line in enumerate(content.splitlines(), start=1):
                    found_vars = self._extract_env_vars_from_line(line)

                    for var_name in found_vars:
                        # Skip excluded variables
                        if var_name in EXCLUDED_VARIABLES:
                            continue

                        location = f"{relative_path}:{line_num}"
                        if var_name not in env_vars:
                            env_vars[var_name] = []
                        if location not in env_vars[var_name]:
                            env_vars[var_name].append(location)

            except Exception as e:
                logger.debug(f"Could not scan file {file_path}: {e}")
                continue

        return env_vars

    def _get_scannable_files(self, repo_dir: Path) -> List[Path]:
        """
        Get list of files to scan for environment variables.

        Args:
            repo_dir: Path to the repository

        Returns:
            List of file paths to scan
        """
        scannable_files = []

        for item in repo_dir.rglob('*'):
            # Skip directories
            if item.is_dir():
                continue

            # Skip excluded directories
            if any(excluded in item.parts for excluded in EXCLUDED_DIRS):
                continue

            # Check if file should be scanned
            if item.name in SCANNABLE_FILES or item.suffix in SCANNABLE_EXTENSIONS:
                scannable_files.append(item)

        return scannable_files

    def _extract_env_vars_from_line(self, line: str) -> Set[str]:
        """
        Extract environment variable names from a line of code.

        Args:
            line: Single line of code

        Returns:
            Set of variable names found in the line
        """
        found_vars = set()

        for pattern, group_num in ENV_VAR_PATTERNS:
            matches = re.finditer(pattern, line)
            for match in matches:
                var_name = match.group(group_num)
                # Only include uppercase variable names (convention for env vars)
                if var_name and var_name.isupper():
                    found_vars.add(var_name)

        return found_vars

    def _parse_env_content_variables(self, env_content: str) -> Set[str]:
        """
        Parse env_content to extract provided variable names.

        Args:
            env_content: Raw .env file content

        Returns:
            Set of variable names provided in env_content
        """
        provided_vars = set()

        for line in env_content.splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Extract variable name (KEY=value format)
            if '=' in line:
                var_name = line.split('=', 1)[0].strip()
                if var_name:
                    provided_vars.add(var_name)

        return provided_vars

    def _build_missing_vars_error(self, missing_vars: Dict[str, List[str]]) -> str:
        """
        Build a detailed error message for missing environment variables.

        Args:
            missing_vars: Dictionary mapping variable names to their locations

        Returns:
            Formatted error message
        """
        lines = [
            "",
            "=" * 60,
            "ENVIRONMENT VARIABLE VALIDATION FAILED",
            "=" * 60,
            "",
            f"Missing variables ({len(missing_vars)}):",
            ""
        ]

        for var_name, locations in sorted(missing_vars.items()):
            lines.append(f"  - {var_name}")
            # Show up to 5 locations per variable
            for loc in locations[:5]:
                lines.append(f"      Referenced in: {loc}")
            if len(locations) > 5:
                lines.append(f"      ... and {len(locations) - 5} more locations")
            lines.append("")

        lines.extend([
            "=" * 60,
            "Please add the missing variables to your env_content and retry.",
            "=" * 60,
            ""
        ])

        return "\n".join(lines)

    async def _process_templates(
        self,
        request: GitOpsManifestRequest,
        env_value: str
    ) -> Dict[str, Any]:
        """Step 1: Process templates with variable substitution"""
        logger.info("[Step 1] Processing templates...")
        await asyncio.sleep(0)

        logger.info("Environment variables provided via env_content")

        # Convert cronjobs models to list of dicts if provided
        cronjobs_list = None
        if request.cronjobs and len(request.cronjobs) > 0:
            cronjobs_list = [cj.model_dump() for cj in request.cronjobs]
            logger.info(f"CronJobs configuration provided: {len(cronjobs_list)} cronjob(s)")
            for idx, cj in enumerate(cronjobs_list):
                logger.info(f"  CronJob [{idx}]: name={cj.get('name')}, schedule={cj.get('schedule')}")
        else:
            logger.info("No CronJobs configuration provided")

        # Convert worker model to dict if provided
        worker_dict = None
        if request.worker:
            worker_dict = request.worker.model_dump()
            logger.info(f"Worker configuration provided: name={worker_dict.get('name')}, type={worker_dict.get('worker_type')}")
        else:
            logger.info("No Worker configuration provided")

        result = self.template_service.process_template(
            microservice_name=request.microservice_name,
            microservice_url=request.microservice_url,
            container_port=request.container_port,
            domain_name=request.domain_name,
            environment=env_value,
            git_repo_name=request.git_repo_name,
            git_branch=request.git_branch,
            git_secret=settings.GITHUB_TOKEN,
            argocd_app_name=request.argocd_app_name,
            gitops_repo_url=request.gitops_repo_url,
            env_content=request.env_content,
            cronjobs=cronjobs_list,
            worker=worker_dict
        )

        logger.info(f"✓ Templates processed successfully")
        return result

    def _build_processed_files(self, result: Dict[str, Any]) -> List[ProcessedFile]:
        """Build ProcessedFile list from template result"""
        return [
            ProcessedFile(
                source_path=pf['source_path'],
                output_path=pf['output_path'],
                replacements_made=pf['replacements_made']
            )
            for pf in result['processed_files']
        ]

    async def _locate_microservice(self, request: GitOpsManifestRequest) -> Path:
        """Step 2: Locate microservice directory"""
        logger.info("[Step 2] Locating microservice...")
        await asyncio.sleep(0)

        repo_dir = self.template_service.output_base_dir
        gitops_path = repo_dir / "git-ops" / request.microservice_name

        if not gitops_path.exists():
            raise Exception(
                f"git-ops folder not found for microservice '{request.microservice_name}'. "
                f"Expected at: {gitops_path}"
            )

        logger.info(f"✓ Found git-ops path at: {gitops_path}")
        return gitops_path

    async def _init_config_service(self, gitops_path: Path) -> ConfigMapService:
        """Step 3: Initialize and validate config service"""
        logger.info("[Step 3] Initializing configuration service...")
        await asyncio.sleep(0)

        config_service = ConfigMapService(gitops_path)
        is_valid, error_msg = config_service.validate_structure()

        if not is_valid:
            raise Exception(f"Invalid microservice structure: {error_msg}")

        logger.info("✓ Configuration service initialized")
        return config_service

    async def _apply_env_variables(
        self,
        request: GitOpsManifestRequest,
        config_service: ConfigMapService
    ) -> None:
        """Step 4 & 5: Parse and apply environment variables"""
        logger.info("[Step 4] Parsing environment variables...")
        await asyncio.sleep(0)

        env_vars = config_service.parse_env_content(request.env_content)
        if not env_vars:
            raise Exception("No valid environment variables found in .env content")

        logger.info(f"✓ Parsed {len(env_vars)} environment variables")

        logger.info("[Step 5] Applying configuration changes...")
        await asyncio.sleep(0)

        changes = config_service.apply_changes(env_vars)
        if not changes:
            logger.info("✓ No changes detected - all values already up to date")
        else:
            logger.info("✓ Configuration changes applied")

    async def _push_gitops_manifests(
        self,
        request: GitOpsManifestRequest,
        env_value: str
    ) -> Path:
        """Step 6: Clone GitOps repository and push manifests"""
        logger.info("[Step 6] Cloning GitOps repository...")
        await asyncio.sleep(0)

        clone_repo_dir = self.project_root / "app" / "temp" / self.template_service.session_id / "repo"
        success, error = git_service.clone_repository(
            request.gitops_repo_url,
            clone_repo_dir,
            branch=env_value
        )

        if not success:
            raise Exception(f"Failed to clone repository: {error}")

        logger.info(f"✓ Repository cloned to: {clone_repo_dir}")

        # Step 7: Move template output to cloned repository
        logger.info("[Step 7] Moving generated manifests to cloned repository...")
        await asyncio.sleep(0)

        source_dir = self.template_service.output_base_dir / "git-ops" / request.microservice_name
        destination_dir = clone_repo_dir / request.microservice_name

        if destination_dir.exists():
            shutil.rmtree(destination_dir)
            logger.info(f"Removed existing directory: {destination_dir}")

        shutil.move(str(source_dir), str(destination_dir))
        logger.info(f"✓ Manifests moved to repository")

        # Step 8: Git commit and push
        logger.info("[Step 8] Committing and pushing changes to Git...")
        await asyncio.sleep(0)

        git_root = git_service.find_git_root(clone_repo_dir)
        if not git_root:
            raise Exception("Could not find git root in cloned repository")

        success, error = await asyncio.to_thread(git_service.add_all, git_root)
        if not success:
            raise Exception(f"Failed to add changes: {error}")

        commit_msg = f"Added/Updated GitOps manifests for {request.microservice_name} in {env_value}"
        success, error, commit_hash = await asyncio.to_thread(
            git_service.commit_changes, git_root, commit_msg
        )

        if not success:
            if "nothing to commit" in str(error).lower():
                logger.info("✓ No changes to commit - manifests already up to date")
            else:
                raise Exception(f"Failed to commit changes: {error}")
        else:
            logger.info(f"✓ Changes committed with hash: {commit_hash}")
            success, error = await asyncio.to_thread(git_service.push_changes, git_root)
            if not success:
                raise Exception(f"Failed to push changes: {error}")
            logger.info("✓ Changes pushed to remote repository")

        return clone_repo_dir

    async def _create_github_secrets(self, request: GitOpsManifestRequest) -> None:
        """Step 9: Create GitHub repository secrets"""
        logger.info("[Step 9] Creating GitHub repository secrets...")
        await asyncio.sleep(0)

        secrets_file = self.template_service.output_base_dir / "github" / request.microservice_name / "secrets.txt"
        repo_name = request.microservice_url.rstrip('/').removesuffix('.git').split('/')[-1]

        if not secrets_file.exists():
            raise Exception(f"Secrets file not found at: {secrets_file}")

        success, error = await asyncio.to_thread(
            git_service.create_repository_secrets,
            secrets_file=secrets_file,
            owner="tehvault",
            repo=repo_name
        )

        if not success:
            raise Exception(f"Failed to create repository secrets: {error}")

        logger.info(f"✓ Repository secrets created for {repo_name}")

    async def _push_github_workflows(
        self,
        request: GitOpsManifestRequest,
        env_value: str
    ) -> str:
        """Step 10 & 11: Clone microservice repo and push GitHub workflows"""
        logger.info("[Step 10] Cloning microservice repository for GitHub workflows...")
        await asyncio.sleep(0)

        microservice_repo_dir = self.project_root / "app" / "temp" / self.template_service.session_id / "microservice-repo"
        success, error = await asyncio.to_thread(
            git_service.clone_repository,
            request.microservice_url,
            microservice_repo_dir,
            branch=env_value
        )

        if not success:
            raise Exception(f"Failed to clone microservice repository: {error}")

        logger.info(f"✓ Microservice repository cloned")

        # Step 11: Setup GitHub workflows
        logger.info("[Step 11] Setting up GitHub workflows...")
        await asyncio.sleep(0)

        workflows_dir = microservice_repo_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        source_workflow = self.template_service.output_base_dir / "github" / request.microservice_name / "workflows.yaml"
        destination_workflow = workflows_dir / f"{env_value}.yaml"

        if source_workflow.exists():
            shutil.move(str(source_workflow), str(destination_workflow))
            logger.info(f"✓ Workflow file moved to: {destination_workflow}")
        else:
            logger.warning(f"Workflow file not found at: {source_workflow}")

        # Step 12: Commit and push GitHub workflows
        logger.info("[Step 12] Committing and pushing GitHub workflows...")
        await asyncio.sleep(0)

        ms_git_root = git_service.find_git_root(microservice_repo_dir)
        if not ms_git_root:
            raise Exception("Could not find git root in microservice repository")

        success, error = await asyncio.to_thread(git_service.add_all, ms_git_root)
        if not success:
            raise Exception(f"Failed to add workflow changes: {error}")

        workflow_commit_msg = f"Added/Updated GitHub workflow for {env_value} environment"
        success, error, workflow_commit_hash = await asyncio.to_thread(
            git_service.commit_changes, ms_git_root, workflow_commit_msg
        )

        if not success:
            if "nothing to commit" in str(error).lower():
                logger.info("✓ No workflow changes to commit")
            else:
                raise Exception(f"Failed to commit workflow changes: {error}")

        # workflow_commit_hash may be None when commit_changes found nothing
        # staged (returns True, None, None). Fall back to current HEAD so the
        # GitHub Actions monitor always has a valid sha.
        if not workflow_commit_hash:
            workflow_commit_hash = await asyncio.to_thread(
                _get_head_commit_hash, ms_git_root
            )
            logger.info(f"Using existing HEAD commit hash: {workflow_commit_hash}")
        else:
            logger.info(f"✓ Workflow changes committed with hash: {workflow_commit_hash}")

        success, error = await asyncio.to_thread(git_service.push_changes, ms_git_root)
        if not success:
            raise Exception(f"Failed to push workflow changes: {error}")

        logger.info("✓ GitHub workflow pushed successfully")
        return workflow_commit_hash

    async def _cleanup_temp_folder(self) -> None:
        """Step 13: Clean up temp folder"""
        logger.info("[Step 13] Cleaning up temp folder...")
        await asyncio.sleep(0)

        temp_session_dir = self.project_root / "app" / "temp" / self.template_service.session_id
        if temp_session_dir.exists():
            shutil.rmtree(temp_session_dir)
            logger.info(f"✓ Cleaned up temp folder")

    async def _create_dns_record(
        self,
        request: GitOpsManifestRequest,
        env_value: str
    ) -> None:
        """Step 14: Create Cloudflare DNS record"""
        logger.info("[Step 14] Creating Cloudflare DNS record...")
        await asyncio.sleep(0)

        cloudflare_service = CloudflareService(
            api_token=settings.CLOUDFLARE_TOKEN,
            env=env_value
        )
        logger.info(f"Using Load Balancer IP for environment '{env_value}': {cloudflare_service.lb_ip}")

        await cloudflare_service.create_dns_record_for_lb(
            zone_id=settings.CLOUDFLARE_ZONE_ID,
            name=request.argocd_app_name
        )
        logger.info(f"✓ Cloudflare DNS record created: {request.argocd_app_name} -> {cloudflare_service.lb_ip}")

    async def _monitor_and_deploy(
        self,
        request: GitOpsManifestRequest,
        argocd_service: ArgoCDService,
        env_value: str,
        workflow_commit_hash: str
    ) -> None:
        """Step 15-18: Monitor GitHub Action and deploy via ArgoCD"""
        logger.info("[Step 15] Monitoring GitHub Action workflow...")
        await asyncio.sleep(0)

        # Wait for GitHub Action to start
        await asyncio.sleep(10)

        # Construct GitHub API URL (supports both HTTPS and SSH remote URLs)
        raw_url = request.microservice_url.rstrip('/')
        raw_url = raw_url.removesuffix('.git')
        if raw_url.startswith("git@"):
            # git@github.com:org/repo  ->  org/repo
            owner_repo = raw_url.split(":", 1)[-1]
        else:
            # https://github.com/org/repo  ->  org/repo
            parts = raw_url.split("github.com/", 1)
            owner_repo = parts[-1] if len(parts) == 2 else raw_url
        github_action_domain = f"https://api.github.com/repos/{owner_repo}"

        github_headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}"
        }

        async with httpx.AsyncClient() as client:
            # Fetch workflow ID with retry logic
            workflow_id = await self._fetch_workflow_id(
                client, github_action_domain, github_headers, workflow_commit_hash
            )

            # Poll workflow status
            await self._poll_workflow_status(
                client, github_action_domain, github_headers, workflow_id
            )

        # Deploy via ArgoCD
        await self._deploy_argocd(request, argocd_service, env_value)

    async def _fetch_workflow_id(
        self,
        client: httpx.AsyncClient,
        github_action_domain: str,
        headers: Dict[str, str],
        commit_hash: str
    ) -> int:
        """Fetch workflow ID from GitHub API with retry logic"""
        logger.info(f"Fetching workflow runs for commit: {commit_hash}")

        workflow_runs_url = f"{github_action_domain}/actions/runs?head_sha={commit_hash}"
        logger.info(f"workflow_runs_url: {workflow_runs_url}")

        for attempt in range(1, WORKFLOW_FETCH_MAX_RETRIES + 1):
            logger.info(f"Fetching workflow runs (attempt {attempt}/{WORKFLOW_FETCH_MAX_RETRIES})...")
            response = await client.get(workflow_runs_url, headers=headers)

            if response.status_code == 200:
                runs_data = response.json()
                workflow_runs = runs_data.get("workflow_runs", [])

                if not workflow_runs:
                    raise Exception(f"No workflow runs found for commit: {commit_hash}")

                workflow_id = workflow_runs[0].get("id")
                logger.info(f"✓ Found workflow ID: {workflow_id}")
                return workflow_id

            elif response.status_code == 404:
                if attempt < WORKFLOW_FETCH_MAX_RETRIES:
                    logger.warning(f"Workflow runs not found (404), retrying in {WORKFLOW_FETCH_RETRY_DELAY}s...")
                    await asyncio.sleep(WORKFLOW_FETCH_RETRY_DELAY)
                else:
                    raise Exception(f"Failed to fetch workflow runs after {WORKFLOW_FETCH_MAX_RETRIES} attempts: {response.text}")
            else:
                raise Exception(f"Failed to fetch workflow runs: {response.text}")

    async def _poll_workflow_status(
        self,
        client: httpx.AsyncClient,
        github_action_domain: str,
        headers: Dict[str, str],
        workflow_id: int
    ) -> None:
        """Poll workflow status until completion"""
        workflow_status = None
        workflow_conclusion = None

        for attempt in range(1, WORKFLOW_POLL_MAX_ATTEMPTS + 1):
            logger.info(f"Polling workflow status (attempt {attempt}/{WORKFLOW_POLL_MAX_ATTEMPTS})...")

            status_url = f"{github_action_domain}/actions/runs/{workflow_id}"
            response = await client.get(status_url, headers=headers)

            if response.status_code != 200:
                raise Exception(f"Failed to fetch workflow status: {response.text}")

            status_data = response.json()
            workflow_status = status_data.get("status")
            workflow_conclusion = status_data.get("conclusion")

            logger.info(f"Workflow status: {workflow_status}, conclusion: {workflow_conclusion}")

            if workflow_status == "completed":
                break

            await asyncio.sleep(WORKFLOW_POLL_INTERVAL)

        if workflow_status != "completed":
            raise Exception(f"Workflow did not complete within timeout. Last status: {workflow_status}")

        if workflow_conclusion != "success":
            raise Exception(f"GitHub Action failed with conclusion: {workflow_conclusion}")

        logger.info("✓ GitHub Action completed successfully")

    async def _deploy_argocd(
        self,
        request: GitOpsManifestRequest,
        argocd_service: ArgoCDService,
        env_value: str
    ) -> None:
        """Create and sync ArgoCD application"""
        if not argocd_service.is_available:
            raise Exception("ArgoCD service is not available")

        # Step 16: Create ArgoCD application
        logger.info("[Step 16] Creating ArgoCD application...")
        await asyncio.sleep(0)

        argocd_service.create_application(
            name=request.argocd_app_name,
            project=env_value,
            repo_url=request.gitops_repo_url,
            path=request.microservice_name,
            target_revision=env_value,
            destination_namespace=request.argocd_app_name
        )
        logger.info(f"✓ ArgoCD application created: {request.microservice_name}")

        # Step 17: Sync ArgoCD application (must sync BEFORE health check)
        logger.info("[Step 17] Syncing ArgoCD application...")
        await asyncio.sleep(0)

        argocd_service.sync_application(request.argocd_app_name)
        logger.info(f"✓ ArgoCD application sync triggered: {request.argocd_app_name}")

        # Step 18: Wait for ArgoCD application to be healthy
        logger.info("[Step 18] Waiting for ArgoCD application to be healthy...")
        await asyncio.sleep(0)

        health_status = await self._poll_argocd_health(argocd_service, request.argocd_app_name)

        if health_status != "Healthy":
            raise Exception(f"ArgoCD application is not healthy within timeout. Last status: {health_status}")

    async def _poll_argocd_health(
        self,
        argocd_service: ArgoCDService,
        app_name: str
    ) -> str:
        """
        Poll ArgoCD application health status.

        Health status meanings:
        - Healthy: All resources are healthy
        - Progressing: Resources are being deployed (transient)
        - Missing: Resources not yet created (transient after sync)
        - Degraded: One or more resources have issues
        - Suspended: Application is suspended
        - Unknown: Health status cannot be determined
        """
        health_status = None
        sync_status = None
        max_attempts = 60

        # Transient states that indicate deployment is still in progress
        transient_states = {"Missing", "Progressing", None}

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Checking ArgoCD health status (attempt {attempt}/{max_attempts})...")

            try:
                app_status = argocd_service.get_application_status(app_name)

                # Get health status
                health_info = app_status.get("health", {})
                health_status = health_info.get("status")

                # Get sync status for additional context
                sync_info = app_status.get("sync", {})
                sync_status = sync_info.get("status")

                logger.info(f"ArgoCD application - Health: {health_status}, Sync: {sync_status}")

                if health_status == "Healthy":
                    logger.info("✓ ArgoCD application is Healthy")
                    return health_status

                if health_status == "Degraded":
                    # Degraded is a terminal failure state
                    logger.error(f"ArgoCD application is Degraded")
                    return health_status

                if health_status == "Suspended":
                    # Suspended apps won't become healthy without intervention
                    logger.warning(f"ArgoCD application is Suspended")
                    return health_status

                # For transient states (Missing, Progressing), continue polling
                if health_status in transient_states:
                    logger.info(f"Status '{health_status}' is transient, continuing to poll...")

            except Exception as e:
                logger.warning(f"Error fetching health status: {e}")

            await asyncio.sleep(HEALTH_POLL_INTERVAL)

        logger.warning(f"Health check timed out. Final status - Health: {health_status}, Sync: {sync_status}")
        return health_status
