"""
HTTP client for Health Service API.
Provides a clean interface for telegram_bot to interact with the health_svc service.
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from config import HEALTH_SVC_API_URL

logger = logging.getLogger(__name__)


class HealthAPIClient:
    """Client for Health Service REST API."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or HEALTH_SVC_API_URL
        if not self.base_url:
            raise ValueError("HEALTH_SVC_API_URL must be set in config")
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip("/")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Raises:
            httpx.HTTPStatusError: For HTTP error responses
            httpx.RequestError: For connection/request errors
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"API error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Request error: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e
    
    # Patient methods
    async def add_patient(self, name: str) -> Dict[str, Any]:
        """
        Add a new patient.
        
        Returns:
            Dict with patient data (id, name, created_at)
        
        Raises:
            ValueError: If patient already exists or API error
            ConnectionError: If connection fails
        """
        return await self._request(
            "POST",
            "/api/v1/patients",
            json={"name": name}
        )
    
    async def get_patients(self) -> List[Dict[str, Any]]:
        """
        Get all patients.
        
        Returns:
            List of patient dicts with id, name, created_at
        
        Raises:
            ConnectionError: If connection fails
        """
        return await self._request("GET", "/api/v1/patients")
    
    # Health record methods
    async def save_record(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        data_type: str,
        value: str
    ) -> Dict[str, Any]:
        """
        Save a health record.
        
        Returns:
            Dict with record data (timestamp, patient, record_type, data_type, value)
        
        Raises:
            ValueError: If patient not found or API error
            ConnectionError: If connection fails
        """
        return await self._request(
            "POST",
            "/api/v1/records",
            json={
                "timestamp": timestamp.isoformat(),
                "patient": patient,
                "record_type": record_type,
                "data_type": data_type,
                "value": value
            }
        )
    
    async def get_records(
        self,
        patient: Optional[str] = None,
        record_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get health records with optional filters.
        
        Args:
            patient: Filter by patient name (optional)
            record_type: Filter by record type (optional)
            limit: Limit number of results (optional)
        
        Returns:
            List of record dicts
        
        Raises:
            ConnectionError: If connection fails
        """
        params = {}
        if patient:
            params["patient"] = patient
        if record_type:
            params["record_type"] = record_type
        if limit:
            params["limit"] = limit
        
        return await self._request("GET", "/api/v1/records", params=params)


# Global client instance
_client_instance: Optional[HealthAPIClient] = None


def get_health_api_client() -> HealthAPIClient:
    """Get or create the global API client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = HealthAPIClient()
    return _client_instance

