"""
Service for uploading medical documents to Paperless NGX using REST API.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

from core.config import (
    PAPERLESS_NGX_URL,
    PAPERLESS_NGX_API_TOKEN,
    PAPERLESS_NGX_TIMEOUT,
    PAPERLESS_NGX_VERIFY_SSL
)

logger = logging.getLogger(__name__)


class PaperlessNgxService:
    """Service for uploading medical documents to Paperless NGX."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[int] = None,
        verify_ssl: Optional[bool] = None
    ):
        """
        Initialize the Paperless NGX service.
        
        Args:
            base_url: Paperless NGX base URL. If not provided, loads from PAPERLESS_NGX_URL env var.
            api_token: API token for authentication. If not provided, loads from PAPERLESS_NGX_API_TOKEN env var.
            timeout: Request timeout in seconds. If not provided, loads from PAPERLESS_NGX_TIMEOUT env var.
            
        Raises:
            ValueError: If base_url or api_token is not provided and not found in environment.
        """
        self.base_url = (base_url or PAPERLESS_NGX_URL).rstrip('/')
        self.api_token = api_token or PAPERLESS_NGX_API_TOKEN
        self.timeout = timeout or PAPERLESS_NGX_TIMEOUT
        self.verify_ssl = verify_ssl if verify_ssl is not None else PAPERLESS_NGX_VERIFY_SSL
        
        if not self.base_url:
            raise ValueError(
                "PAPERLESS_NGX_URL environment variable is required. "
                "Set it or pass base_url parameter."
            )
        
        if not self.api_token:
            raise ValueError(
                "PAPERLESS_NGX_API_TOKEN environment variable is required. "
                "Set it or pass api_token parameter."
            )
        
        # Construct the upload endpoint
        self.upload_endpoint = f"{self.base_url}/api/documents/post_document/"
        
        # Set up default headers
        self.headers = {
            "Authorization": f"Token {self.api_token}"
        }
    
    def upload_medical_document(
        self,
        document_path: str,
        patient_name: str,
        date: str,
        hospital_name: str,
        json_extraction: Dict[str, Any],
        title: Optional[str] = None,
        correspondent_id: Optional[int] = None,
        document_type_id: Optional[int] = None,
        tag_ids: Optional[list[int]] = None
    ) -> Dict[str, Any]:
        """
        Upload a medical document to Paperless NGX with metadata for searchability.
        
        This method:
        1. Validates the document file exists
        2. Creates a searchable title from patient name, hospital, and date
        3. Prepares metadata including JSON extraction for searchability
        4. Uploads the document to Paperless NGX via REST API
        5. Returns the upload result
        
        Args:
            document_path: Path to the document file to upload.
            patient_name: Name of the patient.
            date: Date of the medical document (format: YYYY-MM-DD or any string).
            hospital_name: Name of the hospital/clinic.
            json_extraction: JSON data extracted from the medical document.
            title: Optional custom title (if not provided, auto-generated).
            correspondent_id: Optional correspondent ID in Paperless NGX.
            document_type_id: Optional document type ID in Paperless NGX.
            tag_ids: Optional list of tag IDs to associate with the document.
            
        Returns:
            dict: Response from Paperless NGX API with upload status.
            
        Raises:
            FileNotFoundError: If the document file doesn't exist.
            httpx.HTTPError: For HTTP request errors.
            ValueError: For validation errors.
        """
        document_path_obj = Path(document_path)
        
        # Validate file exists
        if not document_path_obj.exists():
            raise FileNotFoundError(f"Document file not found: {document_path}")
        
        if not document_path_obj.is_file():
            raise ValueError(f"Path is not a file: {document_path}")
        
        # Generate searchable title if not provided
        if not title:
            # Format: "Medical Report - {Patient Name} - {Hospital} - {Date}"
            title = f"Medical Report - {patient_name} - {hospital_name} - {date}"
        
        # Create a comprehensive title that includes key searchable terms
        # Paperless NGX will OCR the document and index it, but including metadata
        # in the title makes it easily searchable from the UI
        searchable_title = f"{title}\n\nPatient: {patient_name}\nHospital: {hospital_name}\nDate: {date}"
        
        # Include JSON extraction summary in title for additional searchability
        # Extract key terms from JSON that might be useful for searching
        if isinstance(json_extraction, dict):
            patient_info = json_extraction.get("patient_info", {})
            hospital_info = json_extraction.get("hospital_info", {})
            if patient_info.get("patient_id"):
                searchable_title += f"\nPatient ID: {patient_info.get('patient_id')}"
            if hospital_info.get("report_type"):
                searchable_title += f"\nReport Type: {hospital_info.get('report_type')}"
        
        # Prepare multipart form data
        # Read file content
        with open(document_path_obj, "rb") as file:
            file_content = file.read()
        
        files = {
            "document": (
                document_path_obj.name,
                file_content,
                self._get_content_type(document_path_obj)
            )
        }
        
        data = {
            "title": searchable_title
        }
        
        # Add optional fields if provided
        if correspondent_id is not None:
            data["correspondent"] = str(correspondent_id)
        
        if document_type_id is not None:
            data["document_type"] = str(document_type_id)
        
        try:
            logger.info(
                f"Uploading medical document to Paperless NGX: {document_path_obj.name} "
                f"(Patient: {patient_name}, Hospital: {hospital_name})"
            )
            
            # Make the upload request
            with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
                # For tags, we need to send them as multiple form fields with the same name
                # httpx supports this by using a list of tuples
                if tag_ids:
                    # Create form data with tags as multiple entries
                    form_data = list(data.items())
                    for tag_id in tag_ids:
                        form_data.append(("tags", str(tag_id)))
                    
                    response = client.post(
                        self.upload_endpoint,
                        headers=self.headers,
                        files=files,
                        data=form_data
                    )
                else:
                    response = client.post(
                        self.upload_endpoint,
                        headers=self.headers,
                        files=files,
                        data=data
                    )
                
                # Check response status
                response.raise_for_status()
                
                logger.info(
                    f"Successfully uploaded document to Paperless NGX: {document_path_obj.name}"
                )
                
                # Paperless NGX typically returns "OK" or a JSON response
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    # If response is not JSON, return text
                    result = {"status": "success", "message": response.text}
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error uploading document to Paperless NGX: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error uploading document to Paperless NGX: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error uploading document to Paperless NGX: {str(e)}",
                exc_info=True
            )
            raise
    
    def _get_content_type(self, file_path: Path) -> str:
        """
        Determine content type based on file extension.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            str: MIME type for the file.
        """
        extension = file_path.suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }
        return content_types.get(extension, "application/octet-stream")
    
    def upload_medical_document_from_dict(
        self,
        document_path: str,
        medical_info: Dict[str, Any],
        title: Optional[str] = None,
        correspondent_id: Optional[int] = None,
        document_type_id: Optional[int] = None,
        tag_ids: Optional[list[int]] = None
    ) -> Dict[str, Any]:
        """
        Upload a medical document using a medical info dictionary.
        
        This is a convenience method that extracts patient name, date, and hospital
        from a medical info dictionary (e.g., from MedicalInfo schema).
        
        Args:
            document_path: Path to the document file to upload.
            medical_info: Dictionary containing hospital_info, patient_info, and optionally biochemistry_results.
            title: Optional custom title.
            correspondent_id: Optional correspondent ID in Paperless NGX.
            document_type_id: Optional document type ID in Paperless NGX.
            tag_ids: Optional list of tag IDs to associate with the document.
            
        Returns:
            dict: Response from Paperless NGX API with upload status.
            
        Raises:
            ValueError: If required fields are missing from medical_info.
        """
        # Extract required information
        hospital_info = medical_info.get("hospital_info", {})
        patient_info = medical_info.get("patient_info", {})
        
        patient_name = patient_info.get("patient_name")
        if not patient_name:
            raise ValueError("patient_info.patient_name is required in medical_info")
        
        hospital_name = hospital_info.get("hospital_name", "Unknown Hospital")
        
        # Extract date from patient_info (could be sample_date or other date field)
        date = patient_info.get("sample_date") or patient_info.get("date") or "Unknown Date"
        
        # Use the full medical_info as json_extraction
        return self.upload_medical_document(
            document_path=document_path,
            patient_name=patient_name,
            date=date,
            hospital_name=hospital_name,
            json_extraction=medical_info,
            title=title,
            correspondent_id=correspondent_id,
            document_type_id=document_type_id,
            tag_ids=tag_ids
        )
