"""
GitOps Manifest Controller
Handles GitOps manifest generation workflow
"""

from typing import Optional, Dict, Any, List

from app.models.gitops import (
    GitOpsManifestRequest,
    GitOpsManifestResponse
)
from app.services.deployment_service import DeploymentService
from app.services.cleanup_service import CleanupService
from app.services.argocd_service import ArgoCDService
from app.core.logging_config import logger


class GitOpsManifestController:
    """
    Controller for GitOps manifest generation

    Orchestrates template processing workflow by delegating to services
    """

    def __init__(self):
        """Initialize controller with service instances"""
        self.deployment_service = DeploymentService()
        self.cleanup_service = CleanupService()
        logger.info("GitOpsManifestController initialized")

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
        return await self.deployment_service.deploy(request, argocd_service)

    async def cleanup_deployment(
        self,
        request: GitOpsManifestRequest,
        argocd_service: ArgoCDService,
        github_secret_names: Optional[List[str]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Cleanup deployment resources

        Args:
            request: GitOps manifest request with cleanup targets
            argocd_service: ArgoCD service instance
            github_secret_names: Optional list of GitHub secret names to delete
            force: Skip safety validations (use with caution)

        Returns:
            Dictionary with cleanup results
        """
        return await self.cleanup_service.cleanup_deployment(
            request=request,
            argocd_service=argocd_service,
            github_secret_names=github_secret_names,
            force=force
        )


# Singleton instance
gitops_manifest_controller = GitOpsManifestController()
