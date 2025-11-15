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
        value: str,
        unit: Optional[str] = None,
        lab_name: Optional[str] = "self"
    ) -> Dict[str, Any]:
        """
        Save a health record.
        
        Args:
            timestamp: When the record was created
            patient: Patient name (must exist in the system)
            record_type: Type of measurement (e.g., 'BP', 'Weight', 'Temperature')
            value: The actual measurement value
            unit: Unit of measurement (optional, e.g., 'mg/dl', 'mmHg', 'kg')
            lab_name: Name of the laboratory or facility (optional, defaults to "self")
        
        Returns:
            Dict with record data (timestamp, patient, record_type, value, unit, lab_name)
        
        Raises:
            ValueError: If patient not found or API error
            ConnectionError: If connection fails
        """
        payload = {
            "timestamp": timestamp.isoformat(),
            "patient": patient,
            "record_type": record_type,
            "value": value
        }
        if unit is not None:
            payload["unit"] = unit
        if lab_name is not None:
            payload["lab_name"] = lab_name
        
        return await self._request(
            "POST",
            "/api/v1/records",
            json=payload
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
    
    async def upload_record_image(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        patient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a medical lab report image.
        
        Args:
            file_content: Binary content of the image file
            filename: Original filename
            content_type: MIME type of the file (e.g., 'image/jpeg')
            patient: Patient name (optional, may be passed as form field or query param)
        
        Returns:
            Dict with upload response (status, filename, message, task_id)
        
        Raises:
            ValueError: If API error occurs
            ConnectionError: If connection fails
        """
        url = f"{self.base_url}/api/v1/records/upload"
        
        # Prepare multipart form data
        files = {
            "file": (filename, file_content, content_type)
        }
        
        # Add patient as form field if provided
        data = {}
        if patient:
            data["patient"] = patient
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:  # Longer timeout for file uploads
                response = await client.post(url, files=files, data=data)
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
    
    async def get_html_view(self, patient_name: str) -> str:
        """
        Get HTML graph view of patient health records.
        
        Args:
            patient_name: Patient name to generate graph for (required)
        
        Returns:
            HTML content as string
        
        Raises:
            ValueError: If API error occurs
            ConnectionError: If connection fails
        """
        url = f"{self.base_url}/api/v1/records/html-view"
        params = {"patient_name": patient_name}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.text
        except httpx.HTTPStatusError as e:
            error_msg = f"API error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Request error: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e


# Global client instance
_client_instance: Optional[HealthAPIClient] = None


def get_health_api_client() -> HealthAPIClient:
    """Get or create the global API client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = HealthAPIClient()
    return _client_instance

