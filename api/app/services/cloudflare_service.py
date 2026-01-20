"""
Cloudflare Service
A service class to interact with Cloudflare API
"""

import httpx
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class DNSRecordCreate(BaseModel):
    """Model for creating DNS records"""
    type: str
    name: str
    content: str
    ttl: Optional[int] = 1
    proxied: Optional[bool] = True
    priority: Optional[int] = None


class CloudflareService:
    """Service class for Cloudflare API operations"""
    
    def __init__(self, api_token: str, email: Optional[str] = None):
        """
        Initialize Cloudflare Service
        
        Args:
            api_token: Cloudflare API Token
            email: Cloudflare account email (optional, for legacy auth)
        """
        self.api_token = api_token
        self.email = email
        self.base_url = "https://api.cloudflare.com/client/v4"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        if self.email:
            headers["X-Auth-Email"] = self.email
            
        return headers
    
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
                raise ValueError(f"Cloudflare API Error: {', '.join(errors)}")
            
            return {
                "success": True,
                "record": data.get("result"),
                "message": "DNS record created successfully"
            }
    
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
                raise ValueError(f"Cloudflare API Error: {', '.join(errors)}")
            
            return {
                "success": True,
                "record": data.get("result"),
                "message": "DNS record updated successfully"
            }
    
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