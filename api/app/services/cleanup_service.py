# app/services/cleanup_service.py
"""
Cleanup Service
Orchestrates the cleanup of deployment resources across multiple services
"""

import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx
import logging

from app.core.logging_config import logger
from app.core.config import get_settings

settings = get_settings()
from app.services.cloudflare_service import CloudflareService, DNSRecordCreate
from app.services.argocd_service import ArgoCDService, ArgoCDAPIException
from app.services.git_service import git_service
from app.models.gitops import GitOpsManifestRequest

class CleanupService:
    """Service for cleaning up deployment resources"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
    
    async def cleanup_deployment(
        self,
        request: GitOpsManifestRequest,
        argocd_service: ArgoCDService,
        github_secret_names: Optional[List[str]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Safely clean up all resources created during deployment workflow.
        
        Performs idempotent cleanup of:
        1. Cloudflare DNS records
        2. ArgoCD applications
        3. GitOps repository manifests
        4. Microservice repository workflows
        5. GitHub repository secrets (optional)
        
        Args:
            request: Original deployment request containing resource identifiers
            argocd_service: Initialized ArgoCD service instance
            github_secret_names: Optional list of secret names to delete
            force: Skip safety checks (not recommended)
        
        Returns:
            Dictionary with cleanup status and detailed results per component
        """
        logger.info("=" * 60)
        logger.info("STARTING DEPLOYMENT CLEANUP")
        logger.info(f"Microservice: {request.microservice_name}")
        logger.info(f"Environment: {request.environment}")
        logger.info(f"Domain: {request.domain_name}")
        logger.info(f"ArgoCD App: {request.argocd_app_name}")
        logger.info("=" * 60)
        
        # Get environment value consistently
        env_value = request.environment.value if hasattr(request.environment, 'value') else str(request.environment)
        
        # Create isolated temp directory for cleanup operations
        cleanup_session_id = f"cleanup_{uuid.uuid4().hex[:8]}"
        temp_base = self.project_root / "app" / "temp" / cleanup_session_id
        temp_base.mkdir(parents=True, exist_ok=True)
        
        results = {
            "success": True,
            "components": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # ==================================================================
            # STEP 1: CLOUDFLARE DNS CLEANUP
            # ==================================================================
            logger.info("\n[STEP 1] Cleaning up Cloudflare DNS records...")
            await asyncio.sleep(0)
            
            try:
                cloudflare_service = CloudflareService(api_token=settings.CLOUDFLARE_TOKEN)
                
                # List existing records matching our domain
                filters = {
                    "name": request.domain_name.lower(),
                    "type": "A"
                }
                existing_records = await cloudflare_service.list_dns_records(
                    zone_id=settings.CLOUDFLARE_ZONE_ID,
                    filters=filters
                )
                
                records_deleted = 0
                if existing_records["records"]:
                    logger.info(f"Found {len(existing_records['records'])} DNS record(s) to delete")
                    for record in existing_records["records"]:
                        try:
                            # Safety check: verify content matches our LB IP before deletion
                            if not force and record.get("content") != settings.LOAD_BALANCER_IP:
                                warning = (f"Skipping DNS record {record['id']} - content mismatch "
                                          f"(expected: {settings.LOAD_BALANCER_IP}, found: {record['content']})")
                                logger.warning(warning)
                                results["warnings"].append(warning)
                                continue
                            
                            await cloudflare_service.delete_dns_record(
                                zone_id=settings.CLOUDFLARE_ZONE_ID,
                                record_id=record["id"]
                            )
                            records_deleted += 1
                            logger.info(f"✓ Deleted DNS record: {record['name']} → {record['content']}")
                        except Exception as e:
                            error_msg = f"Failed to delete DNS record {record.get('id', 'unknown')}: {str(e)}"
                            logger.error(error_msg)
                            results["errors"].append(error_msg)
                            results["success"] = False
                    
                    if records_deleted == 0 and not results["errors"]:
                        logger.info("✓ No DNS records required deletion (already clean)")
                else:
                    logger.info("✓ No matching DNS records found (already clean)")
                
                results["components"]["cloudflare_dns"] = {
                    "status": "success" if not results["errors"] else "partial_failure",
                    "records_deleted": records_deleted,
                    "records_found": len(existing_records["records"])
                }
                
            except Exception as e:
                error_msg = f"Cloudflare cleanup failed: {str(e)}"
                logger.exception(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False
                results["components"]["cloudflare_dns"] = {"status": "failed", "error": str(e)}
            
            await asyncio.sleep(1)
            
            # ==================================================================
            # STEP 2: ARGOCD APPLICATION CLEANUP
            # ==================================================================
            logger.info("\n[STEP 2] Cleaning up ArgoCD application...")
            await asyncio.sleep(0)
            
            try:
                if not argocd_service.is_available:
                    raise Exception("ArgoCD service unavailable")
                
                # Check if application exists before attempting deletion
                try:
                    app_status = argocd_service.get_application_status(request.argocd_app_name)
                    logger.info(f"ArgoCD application '{request.argocd_app_name}' exists")
                    
                    # Safety check: verify namespace matches expected value
                    namespace = app_status.get("spec", {}).get("destination", {}).get("namespace")
                    if not force and namespace != request.argocd_app_name:
                        warning = (f"Skipping ArgoCD app deletion - namespace mismatch "
                                  f"(expected: {request.argocd_app_name}, found: {namespace})")
                        logger.warning(warning)
                        results["warnings"].append(warning)
                        results["components"]["argocd"] = {"status": "skipped", "reason": "namespace_mismatch"}
                    else:
                        # First, delete resources from cluster before removing app definition
                        try:
                            argocd_service.delete_application_resources(request.argocd_app_name)
                            logger.info("✓ Deleted Kubernetes resources from cluster")
                        except Exception as e:
                            logger.warning(f"Resource deletion warning (continuing): {str(e)}")
                        
                        # Now delete the application definition
                        argocd_service.delete_application(request.argocd_app_name)
                        logger.info(f"✓ Deleted ArgoCD application: {request.argocd_app_name}")
                        results["components"]["argocd"] = {"status": "success"}
                except ArgoCDAPIException as e:
                    if e.status_code == 404:
                        logger.info(f"✓ ArgoCD application '{request.argocd_app_name}' not found (already clean)")
                        results["components"]["argocd"] = {"status": "not_found"}
                    else:
                        raise
                
            except Exception as e:
                error_msg = f"ArgoCD cleanup failed: {str(e)}"
                logger.exception(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False
                results["components"]["argocd"] = {"status": "failed", "error": str(e)}
            
            await asyncio.sleep(1)
            
            # ==================================================================
            # STEP 3: GITOPS REPOSITORY CLEANUP
            # ==================================================================
            logger.info("\n[STEP 3] Cleaning up GitOps repository...")
            await asyncio.sleep(0)
            
            gitops_clone_dir = temp_base / "gitops-repo"
            try:
                # Clone repository
                success, error = await asyncio.to_thread(
                    git_service.clone_repository,
                    request.gitops_repo_url,
                    gitops_clone_dir
                )
                if not success:
                    raise Exception(f"Clone failed: {error}")
                
                # Check if microservice directory exists
                microservice_dir = gitops_clone_dir / request.microservice_name
                if not microservice_dir.exists():
                    logger.info(f"✓ Microservice directory '{request.microservice_name}' not found (already clean)")
                    results["components"]["gitops_repo"] = {"status": "not_found"}
                else:
                    # Safety check: verify directory contains expected Helm structure
                    if not force and not (microservice_dir / "Chart.yaml").exists():
                        warning = f"Skipping deletion - '{request.microservice_name}' doesn't appear to be a Helm chart directory"
                        logger.warning(warning)
                        results["warnings"].append(warning)
                        results["components"]["gitops_repo"] = {"status": "skipped", "reason": "invalid_structure"}
                    else:
                        # Remove directory
                        shutil.rmtree(microservice_dir)
                        logger.info(f"✓ Removed microservice directory: {request.microservice_name}")
                        
                        # Commit and push changes
                        git_root = git_service.find_git_root(gitops_clone_dir)
                        await asyncio.to_thread(git_service.add_all, git_root)
                        
                        commit_msg = f"Cleanup: Removed {request.microservice_name} manifests"
                        success, error, commit_hash = await asyncio.to_thread(
                            git_service.commit_changes, git_root, commit_msg
                        )
                        
                        if success:
                            await asyncio.to_thread(git_service.push_changes, git_root)
                            logger.info(f"✓ Pushed cleanup commit: {commit_hash}")
                            results["components"]["gitops_repo"] = {
                                "status": "success",
                                "commit_hash": commit_hash
                            }
                        else:
                            if "nothing to commit" in str(error).lower():
                                logger.info("✓ No changes to commit (directory already removed)")
                                results["components"]["gitops_repo"] = {"status": "already_clean"}
                            else:
                                raise Exception(f"Commit failed: {error}")
            
            except Exception as e:
                error_msg = f"GitOps repo cleanup failed: {str(e)}"
                logger.exception(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False
                results["components"]["gitops_repo"] = {"status": "failed", "error": str(e)}
            finally:
                # Clean up clone directory
                if gitops_clone_dir.exists():
                    shutil.rmtree(gitops_clone_dir, ignore_errors=True)
            
            await asyncio.sleep(1)
            
            # ==================================================================
            # STEP 4: MICROSERVICE REPOSITORY CLEANUP
            # ==================================================================
            logger.info("\n[STEP 4] Cleaning up microservice repository...")
            await asyncio.sleep(0)
            
            microservice_clone_dir = temp_base / "microservice-repo"
            try:
                # Clone specific environment branch
                success, error = await asyncio.to_thread(
                    git_service.clone_repository,
                    request.microservice_url,
                    microservice_clone_dir,
                    branch=env_value
                )
                if not success:
                    # Try main/master branch as fallback for workflow cleanup
                    logger.warning(f"Failed to clone {env_value} branch, trying main branch...")
                    success, error = await asyncio.to_thread(
                        git_service.clone_repository,
                        request.microservice_url,
                        microservice_clone_dir,
                        branch="main"
                    )
                    if not success:
                        raise Exception(f"Clone failed on all branches: {error}")
                
                # Locate and remove workflow file
                workflow_file = microservice_clone_dir / ".github" / "workflows" / f"{env_value}.yaml"
                if not workflow_file.exists():
                    logger.info(f"✓ Workflow file '{env_value}.yaml' not found (already clean)")
                    results["components"]["microservice_repo"] = {"status": "not_found"}
                else:
                    # Safety check: verify file contains expected microservice name
                    if not force:
                        try:
                            content = workflow_file.read_text()
                            if request.microservice_name not in content:
                                warning = (f"Skipping workflow deletion - file doesn't contain microservice name "
                                          f"'{request.microservice_name}'")
                                logger.warning(warning)
                                results["warnings"].append(warning)
                                results["components"]["microservice_repo"] = {
                                    "status": "skipped", 
                                    "reason": "content_mismatch"
                                }
                                workflow_file = None
                        except Exception as e:
                            logger.warning(f"Could not verify workflow content: {str(e)}")
                    
                    if workflow_file and workflow_file.exists():
                        workflow_file.unlink()
                        logger.info(f"✓ Removed workflow file: .github/workflows/{env_value}.yaml")
                        
                        # Commit and push changes
                        git_root = git_service.find_git_root(microservice_clone_dir)
                        await asyncio.to_thread(git_service.add_all, git_root)
                        
                        commit_msg = f"Cleanup: Removed {env_value} workflow"
                        success, error, commit_hash = await asyncio.to_thread(
                            git_service.commit_changes, git_root, commit_msg
                        )
                        
                        if success:
                            await asyncio.to_thread(git_service.push_changes, git_root)
                            logger.info(f"✓ Pushed workflow cleanup commit: {commit_hash}")
                            results["components"]["microservice_repo"] = {
                                "status": "success",
                                "commit_hash": commit_hash
                            }
                        else:
                            if "nothing to commit" in str(error).lower():
                                logger.info("✓ No changes to commit (file already removed)")
                                results["components"]["microservice_repo"] = {"status": "already_clean"}
                            else:
                                raise Exception(f"Commit failed: {error}")
            
            except Exception as e:
                error_msg = f"Microservice repo cleanup failed: {str(e)}"
                logger.exception(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False
                results["components"]["microservice_repo"] = {"status": "failed", "error": str(e)}
            finally:
                # Clean up clone directory
                if microservice_clone_dir.exists():
                    shutil.rmtree(microservice_clone_dir, ignore_errors=True)
            
            await asyncio.sleep(1)
            
            # ==================================================================
            # STEP 5: GITHUB SECRETS CLEANUP (OPTIONAL)
            # ==================================================================
            if github_secret_names:
                logger.info(f"\n[STEP 5] Cleaning up GitHub secrets ({len(github_secret_names)} secrets)...")
                await asyncio.sleep(0)
                
                try:
                    # Extract repo info from URL
                    repo_url_parts = request.microservice_url.rstrip('/').removesuffix('.git').split('/')
                    repo_name = repo_url_parts[-1]
                    owner = repo_url_parts[-2] if len(repo_url_parts) > 1 else "allvest-wm"
                    
                    deleted_secrets = []
                    failed_secrets = []
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        for secret_name in github_secret_names:
                            try:
                                url = f"https://api.github.com/repos/{owner}/{repo_name}/actions/secrets/{secret_name}"
                                headers = {
                                    "Accept": "application/vnd.github.v3+json",
                                    "Authorization": f"Bearer {settings.GITHUB_TOKEN}"
                                }
                                
                                # First check if secret exists
                                check_resp = await client.get(url, headers=headers)
                                if check_resp.status_code == 404:
                                    logger.info(f"  → Secret '{secret_name}' not found (skipping)")
                                    continue
                                
                                # Delete the secret
                                delete_resp = await client.delete(url, headers=headers)
                                if delete_resp.status_code == 204:
                                    logger.info(f"  ✓ Deleted secret: {secret_name}")
                                    deleted_secrets.append(secret_name)
                                else:
                                    error_detail = delete_resp.text[:200] if delete_resp.text else "No details"
                                    logger.error(f"  ✗ Failed to delete secret '{secret_name}': {delete_resp.status_code} - {error_detail}")
                                    failed_secrets.append(f"{secret_name}: {delete_resp.status_code}")
                            
                            except Exception as e:
                                logger.error(f"  ✗ Error deleting secret '{secret_name}': {str(e)}")
                                failed_secrets.append(f"{secret_name}: {str(e)}")
                    
                    results["components"]["github_secrets"] = {
                        "status": "success" if not failed_secrets else "partial_failure",
                        "secrets_deleted": deleted_secrets,
                        "secrets_failed": failed_secrets
                    }
                    
                    if failed_secrets:
                        results["success"] = False
                        results["errors"].append(f"Failed to delete {len(failed_secrets)} GitHub secrets")
                    
                except Exception as e:
                    error_msg = f"GitHub secrets cleanup failed: {str(e)}"
                    logger.exception(error_msg)
                    results["errors"].append(error_msg)
                    results["success"] = False
                    results["components"]["github_secrets"] = {"status": "failed", "error": str(e)}
            else:
                logger.info("\n[STEP 5] Skipping GitHub secrets cleanup (no secret names provided)")
                results["components"]["github_secrets"] = {"status": "skipped", "reason": "no_secrets_provided"}
            
            # ==================================================================
            # FINAL SUMMARY
            # ==================================================================
            logger.info("\n" + "=" * 60)
            logger.info("CLEANUP SUMMARY")
            logger.info("=" * 60)
            
            for component, status in results["components"].items():
                status_icon = "✓" if status["status"] in ["success", "not_found", "already_clean"] else "✗"
                logger.info(f"{status_icon} {component:20s} : {status['status']}")
            
            if results["warnings"]:
                logger.warning("\nWarnings:")
                for warning in results["warnings"]:
                    logger.warning(f"  ⚠ {warning}")
            
            if results["errors"]:
                logger.error("\nErrors:")
                for error in results["errors"]:
                    logger.error(f"  ✗ {error}")
                logger.error("\n✗ Cleanup completed with ERRORS")
            elif results["warnings"]:
                logger.warning("\n⚠ Cleanup completed with WARNINGS")
            else:
                logger.info("\n✓ Cleanup completed successfully")
            
            logger.info("=" * 60)
            
            return results
            
        finally:
            # Always clean up temp directory
            try:
                if temp_base.exists():
                    shutil.rmtree(temp_base, ignore_errors=True)
                    logger.debug(f"Cleaned up temporary directory: {temp_base}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_base}: {str(e)}")