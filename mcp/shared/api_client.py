"""
Shared FastAPI client for MCP servers
Provides unified interface to interact with your FastAPI backend
"""

import httpx
import json
from typing import Optional, Dict, Any, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class FastAPIClient:
    """
    Client for interacting with your FastAPI backend from MCP servers
    
    Features:
    - Automatic token management
    - Request/response logging
    - Error handling
    - Streaming support for deployment endpoints
    """
    
    def __init__(
        self, 
        base_url: str, 
        token: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize FastAPI client
        
        Args:
            base_url: Base URL of FastAPI server (e.g., http://localhost:8000)
            token: Authentication token (optional)
            timeout: Default timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "MCP-Server/1.0"
        }
        
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def _log_request(self, method: str, endpoint: str, **kwargs):
        """Log outgoing request"""
        logger.debug(f"{method} {self.base_url}{endpoint}")
        if kwargs.get('json'):
            logger.debug(f"Request body: {json.dumps(kwargs['json'], indent=2)}")
    
    def _log_response(self, response: httpx.Response):
        """Log response"""
        logger.debug(f"Response status: {response.status_code}")
        if response.status_code >= 400:
            logger.error(f"Response error: {response.text}")
    
    async def post(
        self, 
        endpoint: str, 
        data: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        POST request to FastAPI
        
        Args:
            endpoint: API endpoint (e.g., /api/deploy)
            data: Request body
            timeout: Override default timeout
            
        Returns:
            Response JSON as dict
            
        Raises:
            httpx.HTTPError: On request failure
        """
        url = f"{self.base_url}{endpoint}"
        timeout_value = timeout or self.timeout
        
        self._log_request("POST", endpoint, json=data)
        
        async with httpx.AsyncClient(timeout=timeout_value) as client:
            response = await client.post(
                url,
                json=data,
                headers=self.headers
            )
            
            self._log_response(response)
            response.raise_for_status()
            
            return response.json()
    
    async def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        GET request to FastAPI
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            timeout: Override default timeout
            
        Returns:
            Response JSON as dict
        """
        url = f"{self.base_url}{endpoint}"
        timeout_value = timeout or self.timeout
        
        self._log_request("GET", endpoint, params=params)
        
        async with httpx.AsyncClient(timeout=timeout_value) as client:
            response = await client.get(
                url,
                params=params,
                headers=self.headers
            )
            
            self._log_response(response)
            response.raise_for_status()
            
            return response.json()
    
    async def stream_post(
        self, 
        endpoint: str, 
        data: Dict[str, Any],
        timeout: float = 600.0
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream POST request (for deployment streaming)
        
        Yields JSON objects from NDJSON stream
        
        Args:
            endpoint: API endpoint
            data: Request body
            timeout: Timeout in seconds (default: 10 minutes for deployments)
            
        Yields:
            Dict for each line in NDJSON stream
            
        Example:
            async for event in client.stream_post('/api/deploy', request_data):
                if event['type'] == 'log':
                    print(event['message'])
                elif event['type'] == 'result':
                    print("Deployment complete!")
        """
        url = f"{self.base_url}{endpoint}"
        
        self._log_request("POST (streaming)", endpoint, json=data)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                url,
                json=data,
                headers=self.headers
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        event = json.loads(line)
                        logger.debug(f"Stream event: {event.get('type')}")
                        yield event
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse stream line: {line[:100]}")
                        continue
    
    async def delete(
        self, 
        endpoint: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        DELETE request to FastAPI
        
        Args:
            endpoint: API endpoint
            timeout: Override default timeout
            
        Returns:
            Response JSON as dict
        """
        url = f"{self.base_url}{endpoint}"
        timeout_value = timeout or self.timeout
        
        self._log_request("DELETE", endpoint)
        
        async with httpx.AsyncClient(timeout=timeout_value) as client:
            response = await client.delete(
                url,
                headers=self.headers
            )
            
            self._log_response(response)
            response.raise_for_status()
            
            return response.json()
    
    async def health_check(self) -> bool:
        """
        Check if FastAPI server is healthy
        
        Returns:
            True if server is reachable and healthy
        """
        try:
            response = await self.get("/health", timeout=5.0)
            return response.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Singleton instance (optional)
_client_instance: Optional[FastAPIClient] = None

def get_api_client(
    base_url: Optional[str] = None,
    token: Optional[str] = None
) -> FastAPIClient:
    """
    Get or create FastAPI client singleton
    
    Args:
        base_url: FastAPI base URL (only used on first call)
        token: Auth token (only used on first call)
        
    Returns:
        FastAPIClient instance
    """
    global _client_instance
    
    if _client_instance is None:
        if base_url is None:
            raise ValueError("base_url required for first client initialization")
        _client_instance = FastAPIClient(base_url, token)
    
    return _client_instance