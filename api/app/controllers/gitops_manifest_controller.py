"""
GitOps Manifest Controller
Handles GitOps manifest generation workflow
"""

from app.models.gitops import (
    GitOpsManifestRequest,
    GitOpsManifestResponse,
    ProcessedFile
)
from app.services.gitops_template_service import gitops_template_service
from app.core.logging_config import logger


class GitOpsManifestController:
    """
    Controller for GitOps manifest generation

    Orchestrates template processing workflow
    """

    def __init__(self):
        """Initialize controller"""
        self.template_service = gitops_template_service
        logger.info("GitOpsManifestController initialized")

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

        try:
            # Convert environment variables to list of dicts if needed
            env_vars = None
            if request.environment_variables:
                env_vars = [
                    {"name": ev.name, "value": ev.value}
                    for ev in request.environment_variables
                ]

            # Get environment value as string
            env_value = request.environment.value if hasattr(request.environment, 'value') else str(request.environment)

            # Process templates
            result = self.template_service.process_template(
                microservice_name=request.microservice_name,
                microservice_url=request.microservice_url,
                container_port=request.container_port,
                domain_name=request.domain_name,
                environment=env_value,
                git_repo_name=request.git_repo_name,
                git_branch=request.git_branch,
                argocd_app_name=request.argocd_app_name,
                gitops_repo_url=request.gitops_repo_url,
                environment_variables=env_vars
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

            response = GitOpsManifestResponse(
                status="success",
                message=f"GitOps manifests generated successfully for {request.microservice_name}",
                microservice_name=request.microservice_name,
                environment=env_value,
                output_directory=result['output_directory'],
                processed_files=processed_files,
                total_files_processed=result['total_files_processed'],
                template_variables=result['template_variables']
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
