"""
GitOps Manifest Controller
Handles GitOps manifest generation workflow
"""

import shutil
import asyncio
import httpx
from pathlib import Path
from typing import Optional
from app.models.gitops import (
    GitOpsManifestRequest,
    GitOpsManifestResponse,
    ProcessedFile
)
from app.services.gitops_template_service import GitOpsTemplateService
from app.services.configmap_service import ConfigMapService
from app.services.git_service import git_service
from app.services.argocd_service import ArgoCDService
from app.services.cloudflare_service import CloudflareService, DNSRecordCreate
from app.core.logging_config import logger
from app.core.config import get_settings
from app.core.exceptions import ArgoCDAPIException

settings = get_settings()


class GitOpsManifestController:
    """
    Controller for GitOps manifest generation

    Orchestrates template processing workflow
    """

    def __init__(self):
        """Initialize controller with new template service instance per request"""
        self.template_service = GitOpsTemplateService()
        logger.info("GitOpsManifestController initialized")

    def _find_microservice_path(
        self,
        repo_dir: Path,
        microservice_name: str
    ) -> Optional[Path]:
        """
        Find the microservice directory within the repository

        Args:
            repo_dir: Base repository directory
            microservice_name: Name of the microservice to find

        Returns:
            Path to the microservice directory or None if not found
        """
        # Direct path: repo_dir/microservice_name
        direct_path = repo_dir / microservice_name
        if direct_path.exists() and direct_path.is_dir():
            logger.info(f"Found microservice at direct path: {direct_path}")
            return direct_path

        # Search in subdirectories
        for subdir in repo_dir.iterdir():
            if subdir.is_dir() and subdir.name == microservice_name:
                logger.info(f"Found microservice in subdirectory: {subdir}")
                return subdir

        # Search recursively for values.yaml which indicates a helm chart
        for values_file in repo_dir.rglob("values.yaml"):
            parent_dir = values_file.parent
            if parent_dir.name == microservice_name:
                logger.info(f"Found microservice via values.yaml: {parent_dir}")
                return parent_dir

        logger.warning(f"Microservice '{microservice_name}' not found in {repo_dir}")
        return None

    async def generate_manifests(
        self,
        request: GitOpsManifestRequest,
        argocd_service: ArgoCDService
    ) -> GitOpsManifestResponse:
        """
        Generate GitOps manifests from templates

        Args:
            request: GitOps manifest generation request
            argocd_service: ArgoCD service instance

        Returns:
            GitOpsManifestResponse with processing results
        """
        logger.info(f"=== Starting Manifest Generation ===")
        logger.info(f"Microservice: {request.microservice_name}")
        logger.info(f"Environment: {request.environment}")
        if request.env_content:
            logger.info(f"Environment variables provided via env_content")

        try:
            # Get environment value as string
            env_value = request.environment.value if hasattr(request.environment, 'value') else str(request.environment)

            # Convert cronjob model to dict if provided
            cronjob_dict = None
            if request.cronjob:
                cronjob_dict = request.cronjob.model_dump()
                logger.info(f"CronJob configuration provided:")
                logger.info(f"  - Name: {cronjob_dict.get('name')}")
                logger.info(f"  - Schedule: {cronjob_dict.get('schedule')}")
                logger.info(f"  - Suspend: {cronjob_dict.get('suspend')}")
                logger.info(f"  - Command: {cronjob_dict.get('cmd')}")
            else:
                logger.info("No CronJob configuration provided - skipping cronjob setup")

            # Process templates with env_content (same format as ConfigMap)
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
                cronjob=cronjob_dict
            )

            # Build response
            processed_files = [
                ProcessedFile(
                    source_path=pf['source_path'],
                    output_path=pf['output_path'],
                    replacements_made=pf['replacements_made']
                )
                for pf in result['processed_files']
            ]

            # Step 2: Locating microservice...
            logger.info("Step 2: Locating microservice...")
            repo_dir = self.template_service.output_base_dir

            # Output structure: repo_dir/git-ops/microservice_name/ (helm chart)
            #                   repo_dir/github/microservice_name/ (github workflows)
            gitops_path = repo_dir / "git-ops" / request.microservice_name

            if not gitops_path.exists():
                raise Exception(
                    f"git-ops folder not found for microservice '{request.microservice_name}'. "
                    f"Expected at: {gitops_path}"
                )

            logger.info(f"Found git-ops path at: {gitops_path}")

            # Step 3: Initialize config service with git-ops path (contains values.yaml and templates/)
            logger.info("Step 3: Initializing configuration service...")
            config_service = ConfigMapService(gitops_path)

            # Validate structure
            is_valid, error_msg = config_service.validate_structure()
            if not is_valid:
                raise Exception(f"Invalid microservice structure: {error_msg}")

            # Step 4: Parse environment variables
            logger.info("Step 4: Parsing environment variables...")
            if not request.env_content:
                raise Exception("No .env content provided in request")

            env_vars = config_service.parse_env_content(request.env_content)

            if not env_vars:
                raise Exception("No valid environment variables found in .env content")

            logger.info(f"Parsed {len(env_vars)} environment variables")

            # Step 5: Apply configuration changes
            logger.info("Step 5: Applying configuration changes...")
            changes = config_service.apply_changes(env_vars)

            if not changes:
                logger.info("No changes detected - all values already up to date")

            # Step 6: Clone GitOps repository
            logger.info("Step 6: Cloning GitOps repository...")
            project_root = Path(__file__).parent.parent.parent
            clone_repo_dir =  project_root / "app" / "temp" / self.template_service.session_id / "repo"
            success, error = git_service.clone_repository(request.gitops_repo_url, clone_repo_dir)

            if not success:
                raise Exception(f"Failed to clone repository: {error}")

            logger.info(f"Repository cloned to: {clone_repo_dir}")

            # Step 7: Move template output folder to cloned repository
            logger.info("Step 7: Moving generated manifests to cloned repository...")
            # Source structure: output_base_dir/git-ops/microservice_name/
            source_dir = self.template_service.output_base_dir / "git-ops" / request.microservice_name
            destination_dir = clone_repo_dir / request.microservice_name

            # Remove destination if it exists (to replace with new manifests)
            if destination_dir.exists():
                shutil.rmtree(destination_dir)
                logger.info(f"Removed existing directory: {destination_dir}")

            # Move the generated manifests to the cloned repo
            shutil.move(str(source_dir), str(destination_dir))
            logger.info(f"Moved manifests from {source_dir} to {destination_dir}")

            # Step 8: Git commit and push
            logger.info("Step 8: Committing and pushing changes to Git...")
            git_committed = False
            git_commit_hash = None

            git_root = git_service.find_git_root(clone_repo_dir)
            if not git_root:
                raise Exception("Could not find git root in cloned repository")

            # Add all changes
            success, error = git_service.add_all(git_root)
            if not success:
                raise Exception(f"Failed to add changes: {error}")

            # Commit changes
            commit_msg = f"Added/Updated GitOps manifests for {request.microservice_name} in {env_value}"
            success, error, commit_hash = git_service.commit_changes(git_root, commit_msg)

            if not success:
                if "nothing to commit" in str(error).lower():
                    logger.info("No changes to commit - manifests already up to date")
                else:
                    raise Exception(f"Failed to commit changes: {error}")
            else:
                git_committed = True
                git_commit_hash = commit_hash
                logger.info(f"Changes committed with hash: {commit_hash}")

                # Push changes
                success, error = git_service.push_changes(git_root)
                if not success:
                    raise Exception(f"Failed to push changes: {error}")

                logger.info("Changes pushed to remote repository successfully!")

            # Step 9: Create GitHub repository secrets
            logger.info("Step 9: Creating GitHub repository secrets...")
            secrets_file = self.template_service.output_base_dir / "github" / request.microservice_name / "secrets.txt"

            # Extract repo name from microservice_url (e.g., https://github.com/owner/repo.git -> repo)
            repo_name = request.microservice_url.rstrip('/').removesuffix('.git').split('/')[-1]
            
            if not secrets_file.exists():
                raise Exception(f"Secrets file not found at: {secrets_file}")

            success, error = git_service.create_repository_secrets(
                secrets_file=secrets_file,
                owner="allvest-wm",
                repo=repo_name
            )

            if not success:
                raise Exception(f"Failed to create repository secrets: {error}")

            logger.info(f"Repository secrets created successfully for {repo_name}")

            # Step 10: Clone microservice repo for GitHub workflows
            logger.info("Step 9: Cloning microservice repository for GitHub workflows...")
            microservice_repo_dir = project_root / "app" / "temp" / self.template_service.session_id / "microservice-repo"
            success, error = git_service.clone_repository(
                request.microservice_url,
                microservice_repo_dir,
                branch=env_value
            )

            if not success:
                raise Exception(f"Failed to clone microservice repository: {error}")

            logger.info(f"Microservice repository cloned to: {microservice_repo_dir}")

            # Step 11: Create .github/workflows folder and move workflow file
            logger.info("Step 11: Setting up GitHub workflows...")
            workflows_dir = microservice_repo_dir / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created workflows directory: {workflows_dir}")

            # Source: temp/{session_id}/github/{microservice_name}/workflows.yaml
            # Destination: .github/workflows/{environment}.yaml
            source_workflow = self.template_service.output_base_dir / "github" / request.microservice_name / "workflows.yaml"
            destination_workflow = workflows_dir / f"{env_value}.yaml"

            if source_workflow.exists():
                shutil.move(str(source_workflow), str(destination_workflow))
                logger.info(f"Moved workflow file to: {destination_workflow}")
            else:
                logger.warning(f"Workflow file not found at: {source_workflow}")

            # Step 12: Commit and push GitHub workflows
            logger.info("Step 12: Committing and pushing GitHub workflows...")
            ms_git_root = git_service.find_git_root(microservice_repo_dir)
            if not ms_git_root:
                raise Exception("Could not find git root in microservice repository")

            success, error = git_service.add_all(ms_git_root)
            if not success:
                raise Exception(f"Failed to add workflow changes: {error}")

            workflow_commit_msg = f"Added/Updated GitHub workflow for {env_value} environment"
            success, error, workflow_commit_hash = git_service.commit_changes(ms_git_root, workflow_commit_msg)

            if not success:
                if "nothing to commit" in str(error).lower():
                    logger.info("No workflow changes to commit")
                else:
                    raise Exception(f"Failed to commit workflow changes: {error}")
            else:
                logger.info(f"Workflow changes committed with hash: {workflow_commit_hash}")

                success, error = git_service.push_changes(ms_git_root)
                if not success:
                    raise Exception(f"Failed to push workflow changes: {error}")

                logger.info("GitHub workflow pushed successfully!")

            # Step 13: Clean up temp folder
            logger.info("Step 13: Cleaning up temp folder...")
            temp_session_dir = project_root / "app" / "temp" / self.template_service.session_id
            if temp_session_dir.exists():
                shutil.rmtree(temp_session_dir)
                logger.info(f"Cleaned up temp folder: {temp_session_dir}")

            # Step 14: Create Cloudflare DNS Record
            logger.info("Step 14: Creating Cloudflare DNS record...")
            cloudflare_service = CloudflareService(api_token=settings.CLOUDFLARE_TOKEN)

            dns_record_data = DNSRecordCreate(
                type="A",
                name=request.argocd_app_name,
                content="34.180.18.42" #TODO Change value for DEV & STAGE
            )

            dns_result = await cloudflare_service.create_dns_record(
                zone_id=settings.CLOUDFLARE_ZONE_ID,
                record_data=dns_record_data
            )
            logger.info(f"Cloudflare DNS record created successfully: {request.argocd_app_name}")

            # Step 15: Monitor GitHub Action and sync ArgoCD
            logger.info("Step 15: Monitoring GitHub Action workflow...")

            # Wait 10 seconds for GitHub Action to start
            await asyncio.sleep(10)

            # Construct GitHub API domain from microservice_url
            # Transform https://github.com/owner/repo to https://api.github.com/repos/owner/repo
            github_action_domain = request.microservice_url.rstrip('/')
            github_action_domain = github_action_domain.replace("https://github.com/", "https://api.github.com/repos/")

            # Set up headers for GitHub API
            github_headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}"
            }

            # Fetch workflow ID with retry logic for 404 (race condition)
            logger.info(f"Fetching workflow runs for commit: {workflow_commit_hash}")
            async with httpx.AsyncClient() as client:
                workflow_runs_url = f"{github_action_domain}/actions/runs?head_sha={workflow_commit_hash}"
                logger.info(f"workflow_runs_url : {workflow_runs_url}")
                max_fetch_retries = 10
                fetch_retry_delay = 10  # seconds
                runs_response = None

                for fetch_attempt in range(1, max_fetch_retries + 1):
                    logger.info(f"Fetching workflow runs (attempt {fetch_attempt}/{max_fetch_retries})...")
                    runs_response = await client.get(workflow_runs_url, headers=github_headers)

                    if runs_response.status_code == 200:
                        break
                    elif runs_response.status_code == 404:
                        if fetch_attempt < max_fetch_retries:
                            logger.warning(f"Workflow runs not found (404), retrying in {fetch_retry_delay}s...")
                            await asyncio.sleep(fetch_retry_delay)
                        else:
                            raise Exception(f"Failed to fetch workflow runs after {max_fetch_retries} attempts: {runs_response.text}")
                    else:
                        # For non-404 errors, raise immediately
                        raise Exception(f"Failed to fetch workflow runs: {runs_response.text}")

                runs_data = runs_response.json()
                workflow_runs = runs_data.get("workflow_runs", [])

                if not workflow_runs:
                    raise Exception(f"No workflow runs found for commit: {workflow_commit_hash}")

                workflow_id = workflow_runs[0].get("id")
                logger.info(f"Found workflow ID: {workflow_id}")

                # Polling loop - check status every 10 seconds
                workflow_status = None
                workflow_conclusion = None
                max_attempts = 60  # Max 10 minutes (60 * 10 seconds)
                attempt = 0

                while attempt < max_attempts:
                    attempt += 1
                    logger.info(f"Polling workflow status (attempt {attempt}/{max_attempts})...")

                    status_url = f"{github_action_domain}/actions/runs/{workflow_id}"
                    status_response = await client.get(status_url, headers=github_headers)

                    if status_response.status_code != 200:
                        raise Exception(f"Failed to fetch workflow status: {status_response.text}")

                    status_data = status_response.json()
                    workflow_status = status_data.get("status")
                    workflow_conclusion = status_data.get("conclusion")

                    logger.info(f"Workflow status: {workflow_status}, conclusion: {workflow_conclusion}")

                    if workflow_status == "completed":
                        break

                    # Wait 10 seconds before next poll
                    await asyncio.sleep(10)

                if workflow_status != "completed":
                    raise Exception(f"Workflow did not complete within timeout. Last status: {workflow_status}")

                # Check conclusion
                if workflow_conclusion == "success":
                    logger.info("GitHub Action completed successfully.")

                    if not argocd_service.is_available:
                        raise Exception("ArgoCD service is not available")

                    # Step 16: Create ArgoCD application
                    logger.info("Step 16: Creating ArgoCD application...")
                    argocd_result = argocd_service.create_application(
                        name=request.argocd_app_name,
                        project=env_value,
                        repo_url=request.gitops_repo_url,
                        path=request.microservice_name,
                        target_revision=env_value,
                        destination_namespace=request.argocd_app_name
                    )
                    logger.info(f"ArgoCD application created successfully: {request.microservice_name}")

                    # Step 17: Wait for ArgoCD application to be created before syncing
                    logger.info("Step 17: Waiting for ArgoCD application to be created...")

                    health_status = None
                    health_max_attempts = 60  # Max 10 minutes (60 * 10 seconds)
                    health_attempt = 0

                    while health_attempt < health_max_attempts:
                        health_attempt += 1
                        logger.info(f"Checking ArgoCD health status (attempt {health_attempt}/{health_max_attempts})...")

                        try:
                            app_status = argocd_service.get_application_status(request.argocd_app_name)
                            health_info = app_status.get("health", {})
                            health_status = health_info.get("status")

                            logger.info(f"ArgoCD application health status: {health_status}")

                            if health_status == "Missing":
                                logger.info("ArgoCD application is Healthy. Proceeding to sync...")
                                break

                        except Exception as health_err:
                            logger.warning(f"Error fetching health status: {health_err}")

                        # Wait 10 seconds before next poll
                        await asyncio.sleep(10)

                    if health_status != "Missing":
                        raise Exception(f"ArgoCD application is not created within timeout. Last status: {health_status}")

                    # Step 18: Sync ArgoCD application
                    logger.info("Step 18: Syncing ArgoCD application...")
                    sync_result = argocd_service.sync_application(request.argocd_app_name)
                    logger.info(f"ArgoCD application synced successfully: {request.argocd_app_name}")

                else:
                    raise Exception(f"GitHub Action failed with conclusion: {workflow_conclusion}")

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
                cronjob=result.get('cronjob')
            )

            logger.info(f"=== Manifest Generation Complete ===")
            logger.info(f"Output directory: {result['output_directory']}")
            logger.info(f"Files processed: {result['total_files_processed']}")

            return response

        except ArgoCDAPIException as e:
            logger.error(f"ArgoCD API error: {str(e)}")
            logger.error(f"ArgoCD status code: {e.status_code}")
            logger.error(f"ArgoCD response: {e.response_text}")
            raise
        except Exception as e:
            logger.error(f"Manifest generation failed: {str(e)}", exc_info=True)
            raise


# Singleton instance
gitops_manifest_controller = GitOpsManifestController()
