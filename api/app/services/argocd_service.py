
import time
import requests
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.exceptions import (
    ApplicationNotFoundException,
    ArgoCDAPIException,
    ProjectNotFoundException,
    TokenExpiredException,
    TokenRenewalFailedException
)
from app.utils.argocd_client import ArgoCDClient
from app.utils.helpers import build_application_spec, extract_application_summary, extract_project_summary

logger = logging.getLogger(__name__)


# =============================================================================
# Environment Configuration
# =============================================================================
# Supported environments and their config suffixes.
# Add new environments here as needed.
#
# Example: For 'dev' environment, the service will look for:
#   - ARGOCD_SERVER_DEV
#   - ARGOCD_USERNAME_DEV
#   - ARGOCD_PASSWORD_DEV
#   - ARGOCD_TOKEN_DEV
# =============================================================================

SUPPORTED_ENVIRONMENTS: Dict[str, str] = {
    "dev": "_DEV",
    "development": "_DEV",
    "test": "_TEST",
    "uat": "_UAT",
    "staging": "_STAGING",
    "prod": "_PROD",
    "production": "_PROD",
}

# Default environment (no suffix - uses base config values)
DEFAULT_ENV = "default"


class EnvironmentConfigError(Exception):
    """Raised when required environment configuration is missing"""
    pass


class ArgoCDService:
    """
    High-level service for ArgoCD operations with environment-aware configuration.

    Supports dynamic environment selection via the 'env' parameter:
    - env='dev' or 'development': Uses ARGOCD_SERVER_DEV, ARGOCD_USERNAME_DEV, etc.
    - env='test': Uses ARGOCD_SERVER_TEST, ARGOCD_USERNAME_TEST, etc.
    - env='uat': Uses ARGOCD_SERVER_UAT, ARGOCD_USERNAME_UAT, etc.
    - env='staging': Uses ARGOCD_SERVER_STAGING, ARGOCD_USERNAME_STAGING, etc.
    - env='prod' or 'production': Uses ARGOCD_SERVER_PROD, ARGOCD_USERNAME_PROD, etc.
    - env=None or 'default': Uses base config (ARGOCD_SERVER, ARGOCD_USERNAME, etc.)
    """

    def __init__(
        self,
        server_url: str,
        auth_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        auto_renew_token: bool = True,
        env: Optional[str] = None
    ):
        """
        Initialize ArgoCD service with environment-specific configuration.

        Args:
            server_url: Default ArgoCD server URL (used if env is None/default)
            auth_token: Default ArgoCD authentication token
            username: Default ArgoCD username for token generation
            password: Default ArgoCD password for token generation
            verify_ssl: Whether to verify SSL certificates
            auto_renew_token: Whether to automatically renew expired tokens
            env: Target environment (e.g., 'dev', 'uat', 'staging', 'prod').
                 Determines which config suffix to use for lookups.
        """
        self.env = env
        self.verify_ssl = verify_ssl
        self.auto_renew_token = auto_renew_token
        self.is_available = False

        # Resolve environment-specific configuration
        resolved_config = self._resolve_environment_config(
            default_server_url=server_url,
            default_token=auth_token,
            default_username=username,
            default_password=password,
            env=env
        )

        self.server_url = resolved_config['server_url']
        self.auth_token = resolved_config['token']
        self.username = resolved_config['username']
        self.password = resolved_config['password']

        logger.info(f"ArgoCD Service initializing for environment: {env or DEFAULT_ENV}")
        logger.info(f"Using ArgoCD server URL: {self.server_url}")
        if self.username:
            logger.info(f"Using credentials for user: {self.username}")

        # Auto-generate token if not provided but username/password are available
        if not self.auth_token and self.username and self.password:
            logger.info("No token provided - generating token from username/password...")
            try:
                self.auth_token = self._login(
                    server_url=self.server_url,
                    username=self.username,
                    password=self.password,
                    verify_ssl=self.verify_ssl
                )
                logger.info("Token generated successfully on initialization")

            except Exception as e:
                logger.error(f"Failed to generate initial token: {e}")
                raise TokenRenewalFailedException(
                    f"Could not generate ArgoCD token for environment '{env or DEFAULT_ENV}': {e}"
                )

        # Initialize client with resolved configuration
        try:
            self.client = ArgoCDClient(
                server_url=self.server_url,
                auth_token=self.auth_token,
                username=self.username,
                password=self.password,
                verify_ssl=verify_ssl
            )
            self.is_available = True
        except Exception as e:
            logger.error(f"Failed to initialize ArgoCD client: {e}")
            self.is_available = False
            self.client = None

    # =========================================================================
    # Environment Configuration Resolution
    # =========================================================================

    @staticmethod
    def _get_env_suffix(env: Optional[str]) -> str:
        """
        Get the configuration suffix for an environment.

        Args:
            env: Environment name (e.g., 'dev', 'uat', 'prod')

        Returns:
            Config suffix (e.g., '_DEV', '_UAT', '_PROD') or empty string for default
        """
        if not env or env.lower() == DEFAULT_ENV:
            return ""

        env_lower = env.lower()
        return SUPPORTED_ENVIRONMENTS.get(env_lower, "")

    @staticmethod
    def _get_config_value(setting_name: str, suffix: str, default_value: Any = None) -> Any:
        """
        Get a configuration value with environment suffix.

        Args:
            setting_name: Base setting name (e.g., 'ARGOCD_SERVER')
            suffix: Environment suffix (e.g., '_DEV', '_UAT')
            default_value: Value to return if setting not found

        Returns:
            Configuration value or default
        """
        try:
            from app.core.config import get_settings
            settings = get_settings()

            # Try environment-specific setting first
            if suffix:
                env_setting_name = f"{setting_name}{suffix}"
                env_value = getattr(settings, env_setting_name, None)
                if env_value:
                    logger.debug(f"Using {env_setting_name}: {env_value}")
                    return env_value

            # Fall back to base setting
            base_value = getattr(settings, setting_name, default_value)
            return base_value

        except Exception as e:
            logger.warning(f"Could not load config value {setting_name}{suffix}: {e}")
            return default_value

    def _resolve_environment_config(
        self,
        default_server_url: str,
        default_token: Optional[str],
        default_username: Optional[str],
        default_password: Optional[str],
        env: Optional[str]
    ) -> Dict[str, Any]:
        """
        Resolve all ArgoCD configuration for the specified environment.

        This method implements the DRY principle by using a single lookup pattern
        for all environment-specific settings.

        Args:
            default_server_url: Default server URL from function parameters
            default_token: Default token from function parameters
            default_username: Default username from function parameters
            default_password: Default password from function parameters
            env: Target environment

        Returns:
            Dictionary with resolved configuration:
            - server_url: ArgoCD server URL
            - token: Authentication token
            - username: Username for auth
            - password: Password for auth

        Raises:
            EnvironmentConfigError: If required environment config is missing
        """
        suffix = self._get_env_suffix(env)
        env_name = env or DEFAULT_ENV

        logger.debug(f"Resolving config for environment '{env_name}' with suffix '{suffix}'")

        # Resolve server URL
        server_url = self._get_config_value('ARGOCD_SERVER', suffix, default_server_url)
        if not server_url:
            raise EnvironmentConfigError(
                f"ARGOCD_SERVER{suffix} is not configured for environment '{env_name}'. "
                f"Please set ARGOCD_SERVER{suffix} in your .env file."
            )
        server_url = server_url.rstrip('/')

        # Resolve credentials
        token = self._get_config_value('ARGOCD_TOKEN', suffix, default_token)
        username = self._get_config_value('ARGOCD_USERNAME', suffix, default_username)
        password = self._get_config_value('ARGOCD_PASSWORD', suffix, default_password)

        # Validate credentials are available
        if not token and not (username and password):
            raise EnvironmentConfigError(
                f"ArgoCD credentials not configured for environment '{env_name}'. "
                f"Please set either ARGOCD_TOKEN{suffix} or both "
                f"ARGOCD_USERNAME{suffix} and ARGOCD_PASSWORD{suffix} in your .env file."
            )

        if suffix and (username or token):
            logger.info(f"Using {env_name}-specific ArgoCD configuration")

        return {
            'server_url': server_url,
            'token': token,
            'username': username,
            'password': password
        }

    # =========================================================================
    # Login / Token Operations
    # =========================================================================

    @staticmethod
    def _login(
        server_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 30
    ) -> str:
        """
        Authenticate with ArgoCD server and obtain a session token.

        This method hits the ArgoCD session endpoint: {base_url}/api/v1/session

        Args:
            server_url: ArgoCD server base URL
            username: ArgoCD username
            password: ArgoCD password
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds

        Returns:
            Authentication token string

        Raises:
            TokenRenewalFailedException: If authentication fails
        """
        url = f"{server_url.rstrip('/')}/api/v1/session"
        payload = {"username": username, "password": password}

        logger.debug(f"Attempting ArgoCD login at: {url}")

        try:
            response = requests.post(
                url,
                json=payload,
                verify=verify_ssl,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()
            token = data.get('token')

            if not token:
                raise TokenRenewalFailedException(
                    "Authentication succeeded but no token in response"
                )

            logger.debug("ArgoCD login successful")
            return token

        except requests.exceptions.ConnectionError as e:
            raise TokenRenewalFailedException(
                f"Cannot connect to ArgoCD server at {server_url}. "
                f"Please verify the server URL and network connectivity. Error: {e}"
            )
        except requests.exceptions.Timeout:
            raise TokenRenewalFailedException(
                f"Connection to ArgoCD server at {server_url} timed out after {timeout}s"
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            error_text = e.response.text if e.response else str(e)

            if status_code == 401:
                raise TokenRenewalFailedException(
                    f"Authentication failed: Invalid username or password"
                )
            else:
                raise TokenRenewalFailedException(
                    f"Authentication failed (HTTP {status_code}): {error_text}"
                )
        except Exception as e:
            raise TokenRenewalFailedException(f"Error during ArgoCD login: {e}")

    @classmethod
    def login_for_environment(
        cls,
        env: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        server_url: Optional[str] = None,
        verify_ssl: bool = True
    ) -> Dict[str, str]:
        """
        Static method to login to ArgoCD for a specific environment.

        This method can be used without instantiating the service, useful for
        health checks, login endpoints, or pre-flight validation.

        Args:
            env: Target environment (e.g., 'dev', 'uat', 'prod')
            username: Override username (uses config if not provided)
            password: Override password (uses config if not provided)
            server_url: Override server URL (uses config if not provided)
            verify_ssl: Whether to verify SSL certificates

        Returns:
            Dictionary with:
            - token: The generated authentication token
            - server_url: The ArgoCD server URL used
            - environment: The environment name

        Raises:
            EnvironmentConfigError: If required configuration is missing
            TokenRenewalFailedException: If authentication fails
        """
        suffix = cls._get_env_suffix(env)
        env_name = env or DEFAULT_ENV

        # Resolve server URL
        resolved_server = server_url or cls._get_config_value('ARGOCD_SERVER', suffix)
        if not resolved_server:
            raise EnvironmentConfigError(
                f"ARGOCD_SERVER{suffix} is not configured for environment '{env_name}'"
            )
        resolved_server = resolved_server.rstrip('/')

        # Resolve credentials
        resolved_username = username or cls._get_config_value('ARGOCD_USERNAME', suffix)
        resolved_password = password or cls._get_config_value('ARGOCD_PASSWORD', suffix)

        if not resolved_username or not resolved_password:
            raise EnvironmentConfigError(
                f"ArgoCD credentials not configured for environment '{env_name}'. "
                f"Please provide username/password or set ARGOCD_USERNAME{suffix} "
                f"and ARGOCD_PASSWORD{suffix} in your .env file."
            )

        # Perform login
        token = cls._login(
            server_url=resolved_server,
            username=resolved_username,
            password=resolved_password,
            verify_ssl=verify_ssl
        )

        return {
            'token': token,
            'server_url': resolved_server,
            'environment': env_name
        }

    @classmethod
    def get_environment_config(cls, env: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the configuration for a specific environment without connecting.

        Useful for checking what configuration is available before attempting
        to create a service instance.

        Args:
            env: Target environment

        Returns:
            Dictionary with configuration status:
            - environment: Environment name
            - suffix: Config suffix used
            - server_url: Configured server URL (or None)
            - server_configured: Boolean
            - credentials_configured: Boolean (token or username+password available)
            - has_token: Boolean
            - has_username_password: Boolean
        """
        suffix = cls._get_env_suffix(env)
        env_name = env or DEFAULT_ENV

        server_url = cls._get_config_value('ARGOCD_SERVER', suffix)
        token = cls._get_config_value('ARGOCD_TOKEN', suffix)
        username = cls._get_config_value('ARGOCD_USERNAME', suffix)
        password = cls._get_config_value('ARGOCD_PASSWORD', suffix)

        has_token = bool(token)
        has_username_password = bool(username and password)

        return {
            'environment': env_name,
            'suffix': suffix,
            'server_url': server_url,
            'server_configured': bool(server_url),
            'credentials_configured': has_token or has_username_password,
            'has_token': has_token,
            'has_username_password': has_username_password
        }

    def generate_token(
        self,
        server_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True
    ) -> str:
        """
        Generate a new ArgoCD token (instance method wrapper).

        Args:
            server_url: ArgoCD server URL
            username: ArgoCD username
            password: ArgoCD password
            verify_ssl: Whether to verify SSL certificates

        Returns:
            Authentication token string
        """
        return self._login(server_url, username, password, verify_ssl)

    def renew_token(
        self,
        server_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        update_env: bool = True
    ) -> str:
        """
        Generate new token and update instance.

        Args:
            server_url: ArgoCD server URL
            username: ArgoCD username
            password: ArgoCD password
            verify_ssl: Whether to verify SSL certificates
            update_env: Unused, kept for backwards compatibility

        Returns:
            New authentication token string
        """
        token = self._login(server_url, username, password, verify_ssl)
        self.auth_token = token
        return token

    # =========================================================================
    # Retry Logic
    # =========================================================================

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

    # =========================================================================
    # Application Operations
    # =========================================================================

    def list_applications(
        self,
        project: Optional[str] = None,
        include_summary: bool = True
    ) -> List[Dict[str, Any]]:
        """List all applications"""
        apps = self._execute_with_retry(self.client.list_applications, project) or []

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
                        logger.info(f"Application {app_name} synced and healthy")
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

            logger.info(f"ArgoCD application {app_name} synced successfully")

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

    # =========================================================================
    # Project Operations
    # =========================================================================

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

    # =========================================================================
    # Repository Operations
    # =========================================================================

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

    # =========================================================================
    # Cluster Operations
    # =========================================================================

    def list_clusters(self, include_summary: bool = True) -> List[Dict[str, Any]]:
        """List all clusters"""
        clusters = self._execute_with_retry(self.client.list_clusters)

        if include_summary:
            return [extract_cluster_summary(cluster) for cluster in clusters]

        return clusters

    def get_cluster(self, cluster_url: str) -> Dict[str, Any]:
        """Get cluster details"""
        return self._execute_with_retry(self.client.get_cluster, cluster_url)

    # =========================================================================
    # System Operations
    # =========================================================================

    def get_version(self) -> Dict[str, Any]:
        """Get ArgoCD version"""
        return self._execute_with_retry(self.client.get_version)

    def get_settings(self) -> Dict[str, Any]:
        """Get ArgoCD settings"""
        return self._execute_with_retry(self.client.get_settings)
