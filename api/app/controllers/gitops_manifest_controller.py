"""
GitOps Manifest Controller
Handles GitOps manifest generation workflow
"""

import shutil
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
from app.core.logging_config import logger
from app.core.config import get_settings

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

    def generate_manifests(
        self,
        request: GitOpsManifestRequest
    ) -> GitOpsManifestResponse:
        """
        Generate GitOps manifests from templates

        Args:
            request: GitOps manifest generation request

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
                env_content=request.env_content
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

            response = GitOpsManifestResponse(
                status="success",
                message=f"GitOps manifests generated successfully for {request.microservice_name}",
                microservice_name=request.microservice_name,
                environment=env_value,
                output_directory=result['output_directory'],
                processed_files=processed_files,
                total_files_processed=result['total_files_processed'],
                template_variables=result['template_variables'],
                environment_variables=result.get('environment_variables', {})
            )

            logger.info(f"=== Manifest Generation Complete ===")
            logger.info(f"Output directory: {result['output_directory']}")
            logger.info(f"Files processed: {result['total_files_processed']}")

            return response

        except Exception as e:
            logger.error(f"Manifest generation failed: {str(e)}", exc_info=True)
            raise


# Singleton instance
gitops_manifest_controller = GitOpsManifestController()
