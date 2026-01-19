"""
ConfigMap Controller
Orchestrates the complete GitOps configuration update workflow
Maps to the original script's main() function and workflow
"""
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from app.models.configmap import (
    ConfigMapUpdateRequest,
    ConfigMapUpdateResponse,
    ConfigMapPreviewRequest,
    ConfigMapPreviewResponse,
    ConfigMapApplyChangesRequest as ConfigMapApplyRequest,
    ConfigMapChange as ConfigChangeDetail
)
from app.services.configmap_service import ConfigMapService
from app.services.git_service import git_service
from app.services.argocd_service import ArgoCDService
from app.core.config import get_settings
from app.core.logging_config import logger

# Get settings
settings = get_settings()

class ConfigMapController:
    """
    Controller for complete GitOps workflow
    Orchestrates: Clone → Update → Commit → Sync
    Mirrors the original script's main() workflow
    """
    
    def __init__(self):
        """Initialize controller"""
        self.preview_sessions: Dict[str, Dict] = {}
        logger.info("ConfigMapController initialized")
    
    def execute_update(self, request: ConfigMapUpdateRequest, argocd_service: ArgoCDService,) -> ConfigMapUpdateResponse:
        """
        Execute complete ConfigMap update workflow
        Maps to original script: main() → apply_changes() → git commit → ArgoCD sync
        
        Args:
            request: ConfigMap update request
            
        Returns:
            ConfigMapUpdateResponse with results
        """
        session_id = str(uuid.uuid4())
        repo_dir = settings.UPLOAD_DIR / session_id / "repo"
        
        try:
            logger.info(f"=== Starting ConfigMap Update Workflow ===")
            logger.info(f"Environment: {request.environment_name}")
            logger.info(f"Microservice: {request.microservice_name}")
            logger.info(f"GitOps URL: {request.gitops_url}")
            logger.info(f"ArgoCD App: {request.argocd_app_name}")
            
            # Step 1: Clone repository
            logger.info("Step 1: Cloning GitOps repository...")
            success, error = git_service.clone_repository(request.gitops_url, repo_dir)
            
            if not success:
                raise Exception(f"Failed to clone repository: {error}")
            
            # Step 2: Find microservice path
            logger.info("Step 2: Locating microservice...")
            microservice_path = self._find_microservice_path(
                repo_dir,
                request.microservice_name
            )
            
            if not microservice_path:
                raise Exception(
                    f"Microservice '{request.microservice_name}' not found in repository. "
                    f"Searched in: {repo_dir}"
                )
            
            logger.info(f"Found microservice at: {microservice_path}")
            
            # Step 3: Initialize config service
            logger.info("Step 3: Initializing configuration service...")
            config_service = ConfigMapService(microservice_path)
            
            # Validate structure
            is_valid, error_msg = config_service.validate_structure()
            if not is_valid:
                raise Exception(f"Invalid microservice structure: {error_msg}")
            
            # Step 4: Parse environment variables
            logger.info("Step 4: Parsing environment variables...")
            env_vars = config_service.parse_env_content(request.env_content)
            
            if not env_vars:
                raise Exception("No valid environment variables found in .env content")
            
            logger.info(f"Parsed {len(env_vars)} environment variables")
            
            # Step 5: Apply configuration changes
            logger.info("Step 5: Applying configuration changes...")
            changes = config_service.apply_changes(env_vars)
            
            if not changes:
                logger.info("No changes detected - all values already up to date")
            
            # Convert changes to response format
            change_details = [
                ConfigChangeDetail(
                    file=c['file'],
                    type=c['type'],
                    key=c['key'],
                    old_value=c.get('old'),
                    new_value=c['new']
                )
                for c in changes
            ]
            
            # Prepare response
            response_data = {
                'status': 'success',
                'message': 'Configuration updated successfully',
                'environment': request.environment_name,
                'microservice': request.microservice_name,
                'changes': change_details,
                'summary': config_service.get_changes_summary(),
                'git_committed': False,
                'git_commit_hash': None,
                'argocd_synced': False
            }
            
            # Step 6: Git operations (if auto_commit enabled)
            if request.auto_commit and changes:
                logger.info("Step 6: Committing changes to Git...")
                
                git_root = git_service.find_git_root(microservice_path)
                if not git_root:
                    logger.warning("Could not find git root, skipping git operations")
                else:
                    # Pull latest changes
                    success, error = git_service.pull_latest(git_root)
                    if not success:
                        logger.warning(f"Git pull failed: {error}, continuing anyway")
                    
                    # Add all changes
                    success, error = git_service.add_all(git_root)
                    if not success:
                        raise Exception(f"Failed to add changes: {error}")
                    
                    # Commit changes
                    commit_msg = f"Updated config for {request.microservice_name} in {request.environment_name}"
                    success, error, commit_hash = git_service.commit_changes(
                        git_root,
                        commit_msg
                    )
                    
                    if not success:
                        raise Exception(f"Failed to commit changes: {error}")
                    
                    response_data['git_committed'] = True
                    response_data['git_commit_hash'] = commit_hash
                    
                    # Push changes
                    success, error = git_service.push_changes(git_root)
                    if not success:
                        raise Exception(f"Failed to push changes: {error}")
                    
                    logger.info("✅ Changes pushed to GitHub successfully!")
            
            # Step 7: ArgoCD sync (if auto_sync_argocd enabled)
            if request.auto_sync_argocd and request.git_committed:
                if argocd_service.is_available():
                    logger.info("Step 7: Syncing ArgoCD application...")
                    
                    
                    success, error = argocd_service.sync_application(
                        request.argocd_app_name,
                        prune=True,
                        wait_for_completion=True,  # Wait until healthy
                        timeout=300,                # 5 minutes
                        return_simple=True          # Get tuple response
                    )
                    
                    if success:
                        response_data['argocd_synced'] = True
                        logger.info("✅ ArgoCD application synced successfully!")
                    else:
                        logger.warning(f"ArgoCD sync failed: {error}")
                        response_data['message'] += f" (ArgoCD sync failed: {error})"
                else:
                    logger.warning("ArgoCD utilities not available, skipping sync")
                    response_data['message'] += " (ArgoCD sync skipped - utilities not available)"
            
            # Cleanup
            git_service.cleanup_repository(repo_dir.parent)
            
            logger.info("=== GitOps Update Workflow Completed ===")
            return ConfigMapUpdateResponse(**response_data)
            
        except Exception as e:
            logger.error(f"GitOps update workflow failed: {str(e)}", exc_info=True)
            
            # Cleanup on error
            if repo_dir.exists():
                git_service.cleanup_repository(repo_dir.parent)
            
            raise
    
    def preview_changes(self, request: ConfigMapPreviewRequest) -> ConfigMapPreviewResponse:
        """
        Preview configuration changes without applying
        Maps to original script: preview_changes()
        
        Args:
            request: Preview request
            
        Returns:
            GitOpsPreviewResponse with preview of changes
        """
        preview_id = str(uuid.uuid4())
        repo_dir = settings.UPLOAD_DIR / preview_id / "repo"
        
        try:
            logger.info(f"=== Starting Preview Workflow ===")
            logger.info(f"Environment: {request.environment_name}")
            logger.info(f"Microservice: {request.microservice_name}")
            
            # Clone repository
            success, error = git_service.clone_repository(request.gitops_url, repo_dir)
            if not success:
                raise Exception(f"Failed to clone repository: {error}")
            
            # Find microservice
            microservice_path = self._find_microservice_path(
                repo_dir,
                request.microservice_name
            )
            
            if not microservice_path:
                raise Exception(f"Microservice '{request.microservice_name}' not found")
            
            # Initialize config service
            config_service = ConfigMapService(microservice_path)
            
            # Parse env vars
            env_vars = config_service.parse_env_content(request.env_content)
            if not env_vars:
                raise Exception("No valid environment variables found")
            
            # Generate preview
            changes = config_service.preview_changes(env_vars)
            
            # Convert changes
            change_details = [
                ConfigChangeDetail(
                    file=c['file'],
                    type=c['type'],
                    key=c['key'],
                    old_value=c.get('old'),
                    new_value=c['new']
                )
                for c in changes
            ]
            
            # Store preview session
            self.preview_sessions[preview_id] = {
                'repo_dir': repo_dir,
                'microservice_path': microservice_path,
                'microservice_name': request.microservice_name,
                'env_vars': env_vars,
                'changes': changes,
                'created_at': datetime.utcnow()
            }
            
            logger.info(f"Preview generated: {len(changes)} changes")
            
            return ConfigMapPreviewResponse(
                status='success',
                message='Preview generated successfully',
                session_id=preview_id,
                environment=request.environment_name,
                microservice=request.microservice_name,
                changes=change_details,
                env_variables=env_vars,
                summary=config_service.get_changes_summary(),
                repository_url=request.gitops_url
            )
            
        except Exception as e:
            logger.error(f"Preview workflow failed: {str(e)}", exc_info=True)
            
            # Cleanup on error
            if repo_dir.exists():
                git_service.cleanup_repository(repo_dir.parent)
            
            raise
    
    def apply_previewed_changes(self, request: ConfigMapApplyRequest) -> ConfigMapUpdateResponse:
        """
        Apply previously previewed changes
        
        Args:
            request: Apply request with preview ID
            
        Returns:
            GitOpsUpdateResponse with results
        """
        # Get preview session
        preview_session = self.preview_sessions.get(request.preview_id)
        if not preview_session:
            raise ValueError(f"Preview session {request.preview_id} not found or expired")
        
        try:
            logger.info(f"=== Applying Previewed Changes ===")
            logger.info(f"Preview ID: {request.preview_id}")
            
            microservice_path = preview_session['microservice_path']
            env_vars = preview_session['env_vars']
            microservice_name = preview_session['microservice_name']
            
            # Initialize config service
            config_service = ConfigMapService(microservice_path)
            
            # Apply changes
            changes = config_service.apply_changes(env_vars)
            
            # Convert changes
            change_details = [
                ConfigChangeDetail(
                    file=c['file'],
                    type=c['type'],
                    key=c['key'],
                    old_value=c.get('old'),
                    new_value=c['new']
                )
                for c in changes
            ]
            
            response_data = {
                'status': 'success',
                'message': 'Changes applied successfully',
                'environment': 'preview',
                'microservice': microservice_name,
                'changes': change_details,
                'summary': config_service.get_changes_summary(),
                'git_committed': False,
                'git_commit_hash': None,
                'argocd_synced': False
            }
            
            # Git operations if requested
            if request.auto_commit:
                git_root = git_service.find_git_root(microservice_path)
                if git_root:
                    # Pull, add, commit, push
                    git_service.pull_latest(git_root)
                    git_service.add_all(git_root)
                    
                    commit_msg = f"Updated config for {microservice_name}"
                    success, error, commit_hash = git_service.commit_changes(
                        git_root,
                        commit_msg
                    )
                    
                    if success:
                        response_data['git_committed'] = True
                        response_data['git_commit_hash'] = commit_hash
                        git_service.push_changes(git_root)
            
            # ArgoCD sync if requested
            if request.auto_sync_argocd and response_data['git_committed']:
                if argocd_service.is_available():
                    # Note: ArgoCD app name would need to be stored in preview session
                    pass  # Implement if needed
            
            # Cleanup
            repo_dir = preview_session['repo_dir']
            git_service.cleanup_repository(repo_dir.parent)
            del self.preview_sessions[request.preview_id]
            
            return ConfigMapUpdateResponse(**response_data)
            
        except Exception as e:
            logger.error(f"Apply workflow failed: {str(e)}", exc_info=True)
            raise
    
    def _find_microservice_path(
        self,
        repo_dir: Path,
        microservice_name: str
    ) -> Optional[Path]:
        """
        Find microservice path in repository
        Searches in common locations
        
        Args:
            repo_dir: Repository directory
            microservice_name: Name of microservice
            
        Returns:
            Path to microservice or None
        """
        # Direct path
        direct_path = repo_dir / microservice_name
        if direct_path.exists() and (direct_path / "values.yaml").exists():
            return direct_path
        
        # Common subdirectories
        search_paths = [
            repo_dir / "services" / microservice_name,
            repo_dir / "microservices" / microservice_name,
            repo_dir / "apps" / microservice_name,
            repo_dir / "applications" / microservice_name,
        ]
        
        for path in search_paths:
            if path.exists() and (path / "values.yaml").exists():
                return path
        
        # Recursive search (limited depth)
        for path in repo_dir.rglob("values.yaml"):
            if microservice_name in str(path):
                return path.parent
        
        return None


# Create singleton instance
configmap_controller = ConfigMapController()