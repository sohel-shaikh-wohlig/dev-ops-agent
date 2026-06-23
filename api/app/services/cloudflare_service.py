"""
Cloudflare Service
A service class to interact with Cloudflare API with environment-aware Load Balancer IP configuration.

Supports dynamic environment selection for Load Balancer IPs:
- env='dev' or 'development': Uses LOAD_BALANCER_IP_DEV
- env='test': Uses LOAD_BALANCER_IP_TEST
- env='uat': Uses LOAD_BALANCER_IP_UAT
- env='staging': Uses LOAD_BALANCER_IP_STAGING
- env='prod' or 'production': Uses LOAD_BALANCER_IP_PROD
- env=None or 'default': Uses base config (LOAD_BALANCER_IP)
"""

import logging
import httpx
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


logger = logging.getLogger(__name__)


# =============================================================================
# Environment Configuration
# =============================================================================
# Supported environments and their config suffixes.
# Add new environments here as needed.
#
# Example: For 'dev' environment, the service will look for:
#   - LOAD_BALANCER_IP_DEV
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


class DNSRecordCreate(BaseModel):
    """Model for creating DNS records"""
    type: str
    name: str
    content: str
    ttl: Optional[int] = 1
    proxied: Optional[bool] = True
    priority: Optional[int] = None


class CloudflareService:
    """
    Service class for Cloudflare API operations with environment-aware configuration.

    Supports dynamic environment selection for Load Balancer IPs via the 'env' parameter:
    - env='dev' or 'development': Uses LOAD_BALANCER_IP_DEV
    - env='uat': Uses LOAD_BALANCER_IP_UAT
    - env='staging': Uses LOAD_BALANCER_IP_STAGING
    - env='prod' or 'production': Uses LOAD_BALANCER_IP_PROD
    - env=None or 'default': Uses base config (LOAD_BALANCER_IP)
    """

    def __init__(
        self,
        api_token: str,
        email: Optional[str] = None,
        env: Optional[str] = None
    ):
        """
        Initialize Cloudflare Service with environment-aware configuration.

        Args:
            api_token: Cloudflare API Token
            email: Cloudflare account email (optional, for legacy auth)
            env: Target environment (e.g., 'dev', 'uat', 'staging', 'prod').
                 Determines which Load Balancer IP to use.
        """
        self.api_token = api_token
        self.email = email
        self.env = env
        self.base_url = "https://api.cloudflare.com/client/v4"

        # Resolve environment-specific Load Balancer IP
        self.lb_ip = self._resolve_load_balancer_ip(env)

        logger.info(f"Cloudflare Service initialized for environment: {env or DEFAULT_ENV}")
        logger.info(f"Using Load Balancer IP: {self.lb_ip}")

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
            setting_name: Base setting name (e.g., 'LOAD_BALANCER_IP')
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

    def _resolve_load_balancer_ip(self, env: Optional[str]) -> str:
        """
        Resolve the Load Balancer IP for the specified environment.

        This method implements the DRY principle by using a single lookup pattern
        for environment-specific Load Balancer IPs.

        Args:
            env: Target environment (e.g., 'dev', 'uat', 'prod')

        Returns:
            Load Balancer IP address string

        Raises:
            EnvironmentConfigError: If required environment config is missing
        """
        suffix = self._get_env_suffix(env)
        env_name = env or DEFAULT_ENV

        logger.debug(f"Resolving Load Balancer IP for environment '{env_name}' with suffix '{suffix}'")

        # Resolve Load Balancer IP
        lb_ip = self._get_config_value('LOAD_BALANCER_IP', suffix)

        if not lb_ip:
            raise EnvironmentConfigError(
                f"LOAD_BALANCER_IP{suffix} is not configured for environment '{env_name}'. "
                f"Please set LOAD_BALANCER_IP{suffix} in your .env file."
            )

        if suffix:
            logger.info(f"Using {env_name}-specific Load Balancer IP: {lb_ip}")

        return lb_ip

    @classmethod
    def get_load_balancer_ip(cls, env: Optional[str] = None) -> str:
        """
        Class method to get Load Balancer IP for an environment without instantiating the service.

        Useful for manifest generation, health checks, or pre-flight validation.

        Args:
            env: Target environment (e.g., 'dev', 'uat', 'prod')

        Returns:
            Load Balancer IP address string

        Raises:
            EnvironmentConfigError: If required configuration is missing
        """
        suffix = cls._get_env_suffix(env)
        env_name = env or DEFAULT_ENV

        lb_ip = cls._get_config_value('LOAD_BALANCER_IP', suffix)

        if not lb_ip:
            raise EnvironmentConfigError(
                f"LOAD_BALANCER_IP{suffix} is not configured for environment '{env_name}'. "
                f"Please set LOAD_BALANCER_IP{suffix} in your .env file."
            )

        return lb_ip

    @classmethod
    def get_environment_config(cls, env: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the Load Balancer configuration for a specific environment without connecting.

        Useful for checking what configuration is available before attempting
        to create a service instance.

        Args:
            env: Target environment

        Returns:
            Dictionary with configuration status:
            - environment: Environment name
            - suffix: Config suffix used
            - load_balancer_ip: Configured LB IP (or None)
            - lb_ip_configured: Boolean
        """
        suffix = cls._get_env_suffix(env)
        env_name = env or DEFAULT_ENV

        lb_ip = cls._get_config_value('LOAD_BALANCER_IP', suffix)

        return {
            'environment': env_name,
            'suffix': suffix,
            'load_balancer_ip': lb_ip,
            'lb_ip_configured': bool(lb_ip)
        }

    # =========================================================================
    # API Request Helpers
    # =========================================================================

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        if self.email:
            headers["X-Auth-Email"] = self.email

        return headers

    # =========================================================================
    # DNS Record Operations
    # =========================================================================

    async def create_dns_record(
        self,
        zone_id: str,
        record_data: DNSRecordCreate
    ) -> Dict[str, Any]:
        """
        Create a DNS Record in Cloudflare

        Args:
            zone_id: The zone ID where the DNS record will be created
            record_data: DNS record configuration

        Returns:
            Created DNS record data

        Raises:
            ValueError: If required fields are missing
            httpx.HTTPError: If API request fails
        """
        if not zone_id:
            raise ValueError("Zone ID is required")

        url = f"{self.base_url}/zones/{zone_id}/dns_records"

        payload = {
            "type": record_data.type.upper(),
            "name": record_data.name,
            "content": record_data.content,
            "ttl": record_data.ttl,
            "proxied": record_data.proxied
        }

        # Add priority for MX records
        if record_data.priority is not None:
            payload["priority"] = record_data.priority

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )

            data = response.json()

            if not data.get("success"):
                errors = [err.get("message", "Unknown error") for err in data.get("errors", [])]
                error_msg = ', '.join(errors)

                # If an identical record already exists, treat as success (idempotent)
                if "identical record already exists" in error_msg.lower():
                    logger.info(f"DNS record '{record_data.name}' already exists — skipping creation")
                    return {
                        "success": True,
                        "record": None,
                        "message": f"DNS record '{record_data.name}' already exists — skipped"
                    }

                raise ValueError(f"Cloudflare API Error: {error_msg}")

            return {
                "success": True,
                "record": data.get("result"),
                "message": "DNS record created successfully"
            }

    async def create_dns_record_for_lb(
        self,
        zone_id: str,
        name: str,
        record_type: str = "A",
        ttl: int = 1,
        proxied: bool = True
    ) -> Dict[str, Any]:
        """
        Create a DNS record pointing to the environment-specific Load Balancer IP.

        This method automatically uses the Load Balancer IP configured for
        the service's environment.

        Args:
            zone_id: The zone ID where the DNS record will be created
            name: DNS record name (e.g., 'app.example.com')
            record_type: DNS record type (default: 'A')
            ttl: Time to live (default: 1 for automatic)
            proxied: Whether to proxy through Cloudflare (default: True)

        Returns:
            Created DNS record data
        """
        record_data = DNSRecordCreate(
            type=record_type,
            name=name,
            content=self.lb_ip,
            ttl=ttl,
            proxied=proxied
        )

        logger.info(f"Creating DNS record '{name}' pointing to LB IP: {self.lb_ip}")
        return await self.create_dns_record(zone_id, record_data)

    async def list_dns_records(
        self,
        zone_id: str,
        filters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get all DNS records for a zone

        Args:
            zone_id: The zone ID
            filters: Optional filters (type, name, content, etc.)

        Returns:
            List of DNS records
        """
        url = f"{self.base_url}/zones/{zone_id}/dns_records"

        params = filters if filters else {}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30.0
            )

            data = response.json()

            if not data.get("success"):
                errors = [err.get("message", "Unknown error") for err in data.get("errors", [])]
                raise ValueError(f"Cloudflare API Error: {', '.join(errors)}")

            return {
                "success": True,
                "records": data.get("result", []),
                "total": len(data.get("result", []))
            }

    async def get_dns_record(
        self,
        zone_id: str,
        record_id: str
    ) -> Dict[str, Any]:
        """
        Get a specific DNS record

        Args:
            zone_id: The zone ID
            record_id: The DNS record ID

        Returns:
            DNS record data
        """
        url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                timeout=30.0
            )

            data = response.json()

            if not data.get("success"):
                errors = [err.get("message", "Unknown error") for err in data.get("errors", [])]
                raise ValueError(f"Cloudflare API Error: {', '.join(errors)}")

            return {
                "success": True,
                "record": data.get("result")
            }

    async def update_dns_record(
        self,
        zone_id: str,
        record_id: str,
        record_data: DNSRecordCreate
    ) -> Dict[str, Any]:
        """
        Update a DNS record

        Args:
            zone_id: The zone ID
            record_id: The DNS record ID to update
            record_data: Updated DNS record configuration

        Returns:
            Updated DNS record data
        """
        url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"

        payload = {
            "type": record_data.type.upper(),
            "name": record_data.name,
            "content": record_data.content,
            "ttl": record_data.ttl,
            "proxied": record_data.proxied
        }

        if record_data.priority is not None:
            payload["priority"] = record_data.priority

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )

            data = response.json()

            if not data.get("success"):
                errors = [err.get("message", "Unknown error") for err in data.get("errors", [])]
                error_msg = ', '.join(errors)

                # If an identical record already exists, treat as success (idempotent)
                if "identical record already exists" in error_msg.lower():
                    logger.info(f"DNS record '{record_data.name}' already exists — skipping creation")
                    return {
                        "success": True,
                        "record": None,
                        "message": f"DNS record '{record_data.name}' already exists — skipped"
                    }

                raise ValueError(f"Cloudflare API Error: {error_msg}")

            return {
                "success": True,
                "record": data.get("result"),
                "message": "DNS record updated successfully"
            }

    async def update_dns_record_to_lb(
        self,
        zone_id: str,
        record_id: str,
        name: str,
        record_type: str = "A",
        ttl: int = 1,
        proxied: bool = True
    ) -> Dict[str, Any]:
        """
        Update a DNS record to point to the environment-specific Load Balancer IP.

        Args:
            zone_id: The zone ID
            record_id: The DNS record ID to update
            name: DNS record name
            record_type: DNS record type (default: 'A')
            ttl: Time to live (default: 1 for automatic)
            proxied: Whether to proxy through Cloudflare (default: True)

        Returns:
            Updated DNS record data
        """
        record_data = DNSRecordCreate(
            type=record_type,
            name=name,
            content=self.lb_ip,
            ttl=ttl,
            proxied=proxied
        )

        logger.info(f"Updating DNS record '{name}' to point to LB IP: {self.lb_ip}")
        return await self.update_dns_record(zone_id, record_id, record_data)

    async def delete_dns_record(
        self,
        zone_id: str,
        record_id: str
    ) -> Dict[str, Any]:
        """
        Delete a DNS record

        Args:
            zone_id: The zone ID
            record_id: The DNS record ID to delete

        Returns:
            Deletion result
        """
        url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers=self._get_headers(),
                timeout=30.0
            )

            data = response.json()

            if not data.get("success"):
                errors = [err.get("message", "Unknown error") for err in data.get("errors", [])]
                raise ValueError(f"Cloudflare API Error: {', '.join(errors)}")

            return {
                "success": True,
                "message": "DNS record deleted successfully"
            }

    # =========================================================================
    # Zone Operations
    # =========================================================================

    async def list_zones(self) -> Dict[str, Any]:
        """
        List all zones in the Cloudflare account

        Returns:
            List of zones
        """
        url = f"{self.base_url}/zones"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                timeout=30.0
            )

            data = response.json()

            if not data.get("success"):
                errors = [err.get("message", "Unknown error") for err in data.get("errors", [])]
                raise ValueError(f"Cloudflare API Error: {', '.join(errors)}")

            return {
                "success": True,
                "zones": data.get("result", []),
                "total": len(data.get("result", []))
            }
