import requests
import urllib3
from typing import Dict, List, Optional, Any

from app.core.exceptions import ArgoCDAPIException, TokenExpiredException

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ArgoCDClient:
    """Low-level ArgoCD API client"""
    
    def __init__(
        self,
        server_url: str,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True
    ):
        self.server_url = server_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        if auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            })
        elif username and password:
            token = self._login(username, password)
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            })
    
    def _login(self, username: str, password: str) -> str:
        """Authenticate with username and password"""
        url = f"{self.server_url}/api/v1/session"
        payload = {"username": username, "password": password}
        
        try:
            response = requests.post(url, json=payload, verify=self.verify_ssl)
            response.raise_for_status()
            token = response.json().get('token')
            
            if not token:
                raise ArgoCDAPIException("No token in response")
            
            return token
        except requests.exceptions.RequestException as e:
            raise ArgoCDAPIException(f"Authentication failed: {str(e)}")
    
    def _is_token_expired_error(self, response: requests.Response) -> bool:
        """Check if error is due to expired token"""
        if response.status_code == 401:
            return True
        
        error_text = response.text.lower()
        return any(phrase in error_text for phrase in [
            'token is expired',
            'token has expired',
            'invalid session',
            'unauthorized'
        ])
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make a request to ArgoCD API"""
        url = f"{self.server_url}/api/v1/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Check for token expiration
            if self._is_token_expired_error(response):
                raise TokenExpiredException("ArgoCD token has expired")
            
            response.raise_for_status()
            
            # Return JSON if available, otherwise empty dict
            return response.json() if response.text else {}
            
        except TokenExpiredException:
            raise
        except requests.exceptions.HTTPError as e:
            raise ArgoCDAPIException(
                message=f"HTTP {response.status_code}: {str(e)}",
                status_code=response.status_code,
                response_text=response.text
            )
        except requests.exceptions.RequestException as e:
            raise ArgoCDAPIException(f"Request failed: {str(e)}")
    
    # ==================== Application Operations ====================
    
    def list_applications(self, project: Optional[str] = None) -> List[Dict]:
        """List all applications"""
        params = {}
        if project:
            params['project'] = project
        
        response = self._request('GET', 'applications', params=params)
        return response.get('items', [])
    
    def get_application(self, app_name: str) -> Dict:
        """Get application details"""
        return self._request('GET', f'applications/{app_name}')
    
    def create_application(self, app_spec: Dict) -> Dict:
        """Create a new application"""
        return self._request('POST', 'applications', json=app_spec)
    
    def update_application(self, app_name: str, app_spec: Dict) -> Dict:
        """Update an existing application"""
        return self._request('PUT', f'applications/{app_name}', json=app_spec)
    
    def delete_application(self, app_name: str, cascade: bool = False) -> Dict:
        """Delete an application"""
        params = {'cascade': str(cascade).lower()}
        return self._request('DELETE', f'applications/{app_name}', params=params)
    
    def sync_application(
        self,
        app_name: str,
        revision: Optional[str] = None,
        prune: bool = False,
        dry_run: bool = False,
        resources: Optional[List[Dict]] = None
    ) -> Dict:
        """Sync an application"""
        payload: Dict[str, Any] = {
            "prune": prune,
            "dryRun": dry_run
        }
        
        if revision:
            payload["revision"] = revision
        
        if resources:
            payload["resources"] = resources
        
        return self._request('POST', f'applications/{app_name}/sync', json=payload)
    
    def rollback_application(self, app_name: str, revision: str) -> Dict:
        """Rollback application to a specific revision"""
        payload = {"revision": revision}
        return self._request('POST', f'applications/{app_name}/rollback', json=payload)
    
    def refresh_application(self, app_name: str) -> Dict:
        """Refresh application"""
        return self._request('GET', f'applications/{app_name}', params={'refresh': 'hard'})
    
    # ==================== Project Operations ====================
    
    def list_projects(self) -> List[Dict]:
        """List all projects"""
        response = self._request('GET', 'projects')
        return response.get('items', [])
    
    def get_project(self, project_name: str) -> Dict:
        """Get project details"""
        return self._request('GET', f'projects/{project_name}')
    
    def create_project(self, project_spec: Dict) -> Dict:
        """Create a new project"""
        return self._request('POST', 'projects', json=project_spec)
    
    def update_project(self, project_name: str, project_spec: Dict) -> Dict:
        """Update a project"""
        return self._request('PUT', f'projects/{project_name}', json=project_spec)
    
    def delete_project(self, project_name: str) -> Dict:
        """Delete a project"""
        return self._request('DELETE', f'projects/{project_name}')
    
    # ==================== Repository Operations ====================
    
    def list_repositories(self) -> List[Dict]:
        """List all repositories"""
        response = self._request('GET', 'repositories')
        return response.get('items', [])
    
    def create_repository(self, repo_spec: Dict) -> Dict:
        """Add a new repository"""
        return self._request('POST', 'repositories', json=repo_spec)
    
    def delete_repository(self, repo_url: str) -> Dict:
        """Remove a repository"""
        # URL encode the repository URL
        import urllib.parse
        encoded_url = urllib.parse.quote(repo_url, safe='')
        return self._request('DELETE', f'repositories/{encoded_url}')
    
    # ==================== Cluster Operations ====================
    
    def list_clusters(self) -> List[Dict]:
        """List all clusters"""
        response = self._request('GET', 'clusters')
        return response.get('items', [])
    
    def get_cluster(self, cluster_url: str) -> Dict:
        """Get cluster details"""
        import urllib.parse
        encoded_url = urllib.parse.quote(cluster_url, safe='')
        return self._request('GET', f'clusters/{encoded_url}')
    
    # ==================== System Operations ====================
    
    def get_version(self) -> Dict:
        """Get ArgoCD version"""
        return self._request('GET', 'version')
    
    def get_settings(self) -> Dict:
        """Get ArgoCD settings"""
        return self._request('GET', 'settings')