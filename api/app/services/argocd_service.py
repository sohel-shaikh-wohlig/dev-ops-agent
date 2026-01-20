
import time
import requests
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.exceptions import ApplicationNotFoundException, ArgoCDAPIException, ProjectNotFoundException, TokenExpiredException, TokenRenewalFailedException
from app.utils.argocd_client import ArgoCDClient
from app.utils.helpers import build_application_spec, extract_application_summary, extract_project_summary

logger = logging.getLogger(__name__)

class ArgoCDService:
    """High-level service for ArgoCD operations"""
    
    def __init__(
        self,
        server_url: str,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        auto_renew_token: bool = True
    ):
        self.server_url = server_url
        self.auth_token = auth_token
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.auto_renew_token = auto_renew_token
        self.is_available = False

        #AUTO-GENERATE TOKEN if not provided but username/password are
        if not self.auth_token and self.username and self.password:
            logger.info("No token provided - generating token from username/password...")
            try:
                self.auth_token = self.generate_token(
                    server_url=self.server_url,
                    username=self.username,
                    password=self.password,
                    verify_ssl=self.verify_ssl
                )
                logger.info("✓ Token generated successfully on initialization")
                    
            except Exception as e:
                logger.error(f"Failed to generate initial token: {e}")
                raise TokenRenewalFailedException(
                    f"Could not generate ArgoCD token: {e}"
                )
        
        # Initialize client
        try:
            self.client = ArgoCDClient(
                server_url=server_url,
                auth_token=self.auth_token,  # Use instance variable (may have been generated)
                username=username,
                password=password,
                verify_ssl=verify_ssl
            )
            self.is_available = True
        except Exception as e:
            logger.error(f"Failed to initialize ArgoCD client: {e}")
            self.is_available = False
            self.client = None

    
    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute function with automatic token renewal on expiry"""
        try:
            return func(*args, **kwargs)
        except TokenExpiredException as e:
            logger.warning(f"Token expired: {e}")
            
            if not self.auto_renew_token:
                raise
            
            if not (self.username and self.password):
                logger.error("Cannot renew token: username and password not provided")
                raise
            
            # Renew token
            try:
                logger.info("Attempting to renew token...")
                new_token = self.renew_token(
                    self.server_url,
                    self.username,
                    self.password,
                    self.verify_ssl,
                    update_env=True
                )
                
                # Update client with new token
                self.auth_token = new_token
                self.client = ArgoCDClient(
                    server_url=self.server_url,
                    auth_token=new_token,
                    verify_ssl=self.verify_ssl
                )
                
                logger.info("Token renewed successfully, retrying operation...")
                return func(*args, **kwargs)
                
            except Exception as renewal_error:
                logger.error(f"Failed to renew token: {renewal_error}")
                raise
            
    # ==================== Application Operations ====================
    
    def list_applications(
        self,
        project: Optional[str] = None,
        include_summary: bool = True
    ) -> List[Dict[str, Any]]:
        """List all applications"""
        apps = self._execute_with_retry(self.client.list_applications, project)
        
        if include_summary:
            return [extract_application_summary(app) for app in apps]
        
        return apps
    
    def get_application(self, app_name: str) -> Dict[str, Any]:
        """Get application details"""
        try:
            return self._execute_with_retry(self.client.get_application, app_name)
        except ArgoCDAPIException as e:
            if e.status_code == 404:
                raise ApplicationNotFoundException(f"Application '{app_name}' not found")
            raise
    
    def create_application(
        self,
        name: str,
        project: str,
        repo_url: str,
        path: str = ".",
        target_revision: str = "HEAD",
        destination_server: str = "https://kubernetes.default.svc",
        destination_namespace: str = "default",
        auto_sync: bool = False,
        auto_prune: bool = False,
        self_heal: bool = False,
        auto_create_namespace: bool = True,
        revision_history_limit: int = 10,
        chart: Optional[str] = None,
        helm_values: Optional[Dict] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a new application"""
        app_spec = build_application_spec(
            name=name,
            project=project,
            repo_url=repo_url,
            path=path,
            target_revision=target_revision,
            destination_server=destination_server,
            destination_namespace=destination_namespace,
            auto_sync=auto_sync,
            auto_prune=auto_prune,
            self_heal=self_heal,
            auto_create_namespace=auto_create_namespace,
            revision_history_limit=revision_history_limit,
            chart=chart,
            helm_values=helm_values,
            labels=labels,
            annotations=annotations
        )
        
        return self._execute_with_retry(self.client.create_application, app_spec)
    
    
    def update_application(
        self,
        app_name: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing application"""
        # Get current application
        current_app = self.get_application(app_name)
        
        # Update fields
        if 'repo_url' in updates:
            current_app['spec']['source']['repoURL'] = updates['repo_url']
        
        if 'path' in updates:
            current_app['spec']['source']['path'] = updates['path']
        
        if 'target_revision' in updates:
            current_app['spec']['source']['targetRevision'] = updates['target_revision']
        
        if 'destination_namespace' in updates:
            current_app['spec']['destination']['namespace'] = updates['destination_namespace']
        
        # Update sync policy
        if any(k in updates for k in ['auto_sync', 'auto_prune', 'self_heal']):
            if 'syncPolicy' not in current_app['spec']:
                current_app['spec']['syncPolicy'] = {}
            
            if updates.get('auto_sync'):
                current_app['spec']['syncPolicy']['automated'] = {
                    'prune': updates.get('auto_prune', False),
                    'selfHeal': updates.get('self_heal', False)
                }
            elif 'auto_sync' in updates and not updates['auto_sync']:
                current_app['spec']['syncPolicy'].pop('automated', None)
        
        return self._execute_with_retry(
            self.client.update_application,
            app_name,
            current_app
        )
    
    def delete_application(
        self,
        app_name: str,
        cascade: bool = False
    ) -> Dict[str, Any]:
        """Delete an application"""
        return self._execute_with_retry(
            self.client.delete_application,
            app_name,
            cascade
        )
    
    def sync_application(
        self,
        app_name: str,
        revision: Optional[str] = None,
        prune: bool = False,
        dry_run: bool = False,
        resources: Optional[List[Dict]] = None,
        wait_for_completion: bool = False,
        timeout: int = 300,
        return_simple: bool = False
    ) -> Union[Dict[str, Any], Tuple[bool, Optional[str]]]:
        """
        Sync an application
        
        Args:
            app_name: Application name
            revision: Specific revision to sync (optional)
            prune: Prune resources
            dry_run: Dry run mode
            resources: Specific resources to sync
            wait_for_completion: Wait until sync completes and app is healthy
            timeout: Timeout in seconds for wait_for_completion
            return_simple: Return (success, error_message) tuple instead of full dict
            
        Returns:
            Dict with sync result OR Tuple(success, error) if return_simple=True
        """
        try:
            # Perform sync
            logger.info(f"Syncing ArgoCD application: {app_name}")
            sync_result = self._execute_with_retry(
                self.client.sync_application,
                app_name,
                revision,
                prune,
                dry_run,
                resources
            )
            
            logger.info(f"Sync initiated for {app_name}")
            
            # Wait for completion if requested
            if wait_for_completion:
                logger.info(f"Waiting for sync to complete (timeout: {timeout}s)...")
                
                start_time = time.time()
                while time.time() - start_time < timeout:
                    status = self.get_application_status(app_name)
                    
                    sync_status = status.get('sync', {}).get('status')
                    health_status = status.get('health', {}).get('status')
                    
                    logger.debug(f"Status: sync={sync_status}, health={health_status}")
                    
                    if sync_status == 'Synced' and health_status == 'Healthy':
                        logger.info(f"✅ Application {app_name} synced and healthy")
                        if return_simple:
                            return True, None
                        return sync_result
                    
                    if health_status == 'Degraded':
                        error_msg = f"Application {app_name} is degraded"
                        logger.warning(error_msg)
                        if return_simple:
                            return False, error_msg
                        return sync_result
                    
                    time.sleep(5)  # Check every 5 seconds
                
                # Timeout reached
                logger.warning(f"Sync timeout reached for {app_name}")
                if return_simple:
                    return False, f"Sync timeout after {timeout} seconds"
                return sync_result
            
            logger.info(f"✅ ArgoCD application {app_name} synced successfully")
            
            if return_simple:
                return True, None
            
            return sync_result
            
        except ApplicationNotFoundException as e:
            error_msg = f"Application not found: {str(e)}"
            logger.error(error_msg)
            if return_simple:
                return False, error_msg
            raise
        except Exception as e:
            error_msg = f"Failed to sync ArgoCD application: {str(e)}"
            logger.error(error_msg)
            if return_simple:
                return False, error_msg
            raise
    
    def rollback_application(
        self,
        app_name: str,
        revision: str
    ) -> Dict[str, Any]:
        """Rollback application to a specific revision"""
        return self._execute_with_retry(
            self.client.rollback_application,
            app_name,
            revision
        )
    
    def refresh_application(self, app_name: str) -> Dict[str, Any]:
        """Refresh application"""
        return self._execute_with_retry(self.client.refresh_application, app_name)
    
    def get_application_status(self, app_name: str) -> Dict[str, Any]:
        """Get application sync and health status"""
        app = self.get_application(app_name)
        status = app.get('status', {})
        
        return {
            'name': app['metadata']['name'],
            'sync': status.get('sync', {}),
            'health': status.get('health', {}),
            'resources': status.get('resources', [])
        }
    
    def get_out_of_sync_applications(
        self,
        project: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all out-of-sync applications"""
        apps = self.list_applications(project=project, include_summary=False)
        
        out_of_sync = []
        for app in apps:
            sync_status = app.get('status', {}).get('sync', {}).get('status')
            if sync_status == 'OutOfSync':
                out_of_sync.append(extract_application_summary(app))
        
        return out_of_sync
    
    def get_unhealthy_applications(
        self,
        project: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all unhealthy applications"""
        apps = self.list_applications(project=project, include_summary=False)
        
        unhealthy = []
        for app in apps:
            health_status = app.get('status', {}).get('health', {}).get('status')
            if health_status != 'Healthy':
                summary = extract_application_summary(app)
                summary['health_message'] = app.get('status', {}).get('health', {}).get('message')
                unhealthy.append(summary)
        
        return unhealthy
    
    def sync_all_out_of_sync_applications(
        self,
        project: Optional[str] = None,
        prune: bool = True
    ) -> List[Dict[str, Any]]:
        """Sync all out-of-sync applications"""
        out_of_sync_apps = self.get_out_of_sync_applications(project)
        
        results = []
        for app in out_of_sync_apps:
            try:
                sync_result = self.sync_application(app['name'], prune=prune)
                results.append({
                    'name': app['name'],
                    'status': 'synced',
                    'result': sync_result
                })
            except Exception as e:
                results.append({
                    'name': app['name'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    # ==================== Project Operations ====================
    
    def list_projects(self, include_summary: bool = True) -> List[Dict[str, Any]]:
        """List all projects"""
        projects = self._execute_with_retry(self.client.list_projects)
        
        if include_summary:
            return [extract_project_summary(proj) for proj in projects]
        
        return projects
    
    def get_project(self, project_name: str) -> Dict[str, Any]:
        """Get project details"""
        try:
            return self._execute_with_retry(self.client.get_project, project_name)
        except ArgoCDAPIException as e:
            if e.status_code == 404:
                raise ProjectNotFoundException(f"Project '{project_name}' not found")
            raise
    
    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        source_repos: Optional[List[str]] = None,
        destinations: Optional[List[Dict[str, str]]] = None,
        cluster_resource_whitelist: Optional[List[Dict[str, str]]] = None,
        namespace_resource_blacklist: Optional[List[Dict[str, str]]] = None,
        roles: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Create a new project"""
        project_spec = build_project_spec(
            name=name,
            description=description,
            source_repos=source_repos,
            destinations=destinations,
            cluster_resource_whitelist=cluster_resource_whitelist,
            namespace_resource_blacklist=namespace_resource_blacklist,
            roles=roles
        )
        
        return self._execute_with_retry(self.client.create_project, project_spec)
    
    def delete_project(self, project_name: str) -> Dict[str, Any]:
        """Delete a project"""
        return self._execute_with_retry(self.client.delete_project, project_name)
    
    # ==================== Repository Operations ====================
    
    def list_repositories(self, include_summary: bool = True) -> List[Dict[str, Any]]:
        """List all repositories"""
        repos = self._execute_with_retry(self.client.list_repositories)
        
        if include_summary:
            return [extract_repository_summary(repo) for repo in repos]
        
        return repos
    
    def create_repository(
        self,
        repo_url: str,
        repo_type: str = "git",
        name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssh_private_key: Optional[str] = None,
        insecure: bool = False,
        tls_client_cert_data: Optional[str] = None,
        tls_client_cert_key: Optional[str] = None,
        enable_oci: bool = False
    ) -> Dict[str, Any]:
        """Add a new repository"""
        repo_spec = build_repository_spec(
            repo_url=repo_url,
            repo_type=repo_type,
            name=name,
            username=username,
            password=password,
            ssh_private_key=ssh_private_key,
            insecure=insecure,
            tls_client_cert_data=tls_client_cert_data,
            tls_client_cert_key=tls_client_cert_key,
            enable_oci=enable_oci
        )
        
        return self._execute_with_retry(self.client.create_repository, repo_spec)
    
    def delete_repository(self, repo_url: str) -> Dict[str, Any]:
        """Remove a repository"""
        return self._execute_with_retry(self.client.delete_repository, repo_url)
    
    # ==================== Cluster Operations ====================
    
    def list_clusters(self, include_summary: bool = True) -> List[Dict[str, Any]]:
        """List all clusters"""
        clusters = self._execute_with_retry(self.client.list_clusters)
        
        if include_summary:
            return [extract_cluster_summary(cluster) for cluster in clusters]
        
        return clusters
    
    def get_cluster(self, cluster_url: str) -> Dict[str, Any]:
        """Get cluster details"""
        return self._execute_with_retry(self.client.get_cluster, cluster_url)
    
    # ==================== System Operations ====================
    
    def get_version(self) -> Dict[str, Any]:
        """Get ArgoCD version"""
        return self._execute_with_retry(self.client.get_version)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get ArgoCD settings"""
        return self._execute_with_retry(self.client.get_settings)
    
    # ==================== Token Operations ====================

    def generate_token(
        self,
        server_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True
    ) -> str:
        """Generate a new ArgoCD token"""
        
        url = f"{server_url.rstrip('/')}/api/v1/session"
        payload = {"username": username, "password": password}
        
        try:
            response = requests.post(url, json=payload, verify=verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            token = data.get('token')
            
            if not token:
                raise TokenRenewalFailedException("No token in response")
            
            return token
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Authentication failed: {e.response.text if e.response else str(e)}"
            raise TokenRenewalFailedException(error_msg)
        except Exception as e:
            raise TokenRenewalFailedException(f"Error generating token: {e}")
        
    def renew_token(
        self,
        server_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        update_env: bool = True
    ) -> str:
        """Generate new token and optionally update .env file"""
        
        token = self.generate_token(server_url, username, password, verify_ssl)
        
        return token
    
    
    