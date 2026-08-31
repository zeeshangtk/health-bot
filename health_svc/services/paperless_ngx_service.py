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
from core.date_utils import parse_sample_date

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
        tag_ids: Optional[list[int]] = None,
        report_type: Optional[str] = None
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
            report_type: Optional report type (e.g. "Laboratory Reports"), tagged
                the same way as patient_name if provided.

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
        
        # Resolve (or create) a tag matching the patient's name, so the document
        # can be found by patient in the Paperless UI. Any failure here fails the
        # whole upload rather than silently archiving an untagged document.
        patient_tag_id = self._get_or_create_tag_id(patient_name)
        resolved_tag_ids = (tag_ids or []) + [patient_tag_id]

        # Also tag by report type when available (same failure semantics as the
        # patient tag - if it's present but the tag API call fails, the whole
        # upload fails; if it's simply absent from the data, there's nothing to tag).
        if report_type:
            resolved_tag_ids.append(self._get_or_create_tag_id(report_type))

        all_tag_ids = list(dict.fromkeys(resolved_tag_ids))

        # Use the actual report/sample date as the document's Paperless "created"
        # date (instead of the upload time) so Paperless's date-range filter works.
        # An unparseable value (e.g. the "Unknown Date" fallback) is expected when
        # extraction didn't find a date - leave "created" unset in that case rather
        # than failing the upload.
        created = None
        try:
            created = parse_sample_date(date).strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(
                f"Could not parse date '{date}' for Paperless 'created' field; leaving unset."
            )

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

        if created is not None:
            data["created"] = created

        # Add optional fields if provided
        if correspondent_id is not None:
            data["correspondent"] = str(correspondent_id)

        if document_type_id is not None:
            data["document_type"] = str(document_type_id)

        if all_tag_ids:
            # For repeated form fields (multiple tags) in a multipart request,
            # httpx needs a dict with a list value - a flat list of (key, value)
            # tuples is only reliably supported for URL-encoded (non-file) requests
            # and raises "expected a bytes-like object, tuple found" when combined
            # with files= here.
            data["tags"] = [str(tag_id) for tag_id in all_tag_ids]

        try:
            logger.info(
                f"Uploading medical document to Paperless NGX: {document_path_obj.name} "
                f"(Patient: {patient_name}, Hospital: {hospital_name})"
            )

            # Make the upload request
            with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
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

    def _get_or_create_tag_id(self, tag_name: str) -> int:
        """
        Look up a Paperless NGX tag by name (case-insensitive), creating it if
        it doesn't exist yet.

        Args:
            tag_name: Name of the tag to find or create.

        Returns:
            int: The ID of the existing or newly created tag.

        Raises:
            httpx.HTTPError: For HTTP request errors.
        """
        tags_endpoint = f"{self.base_url}/api/tags/"

        with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
            response = client.get(
                tags_endpoint,
                headers=self.headers,
                params={"name__iexact": tag_name}
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]

            try:
                response = client.post(
                    tags_endpoint,
                    headers=self.headers,
                    json={"name": tag_name}
                )
                response.raise_for_status()
                return response.json()["id"]
            except httpx.HTTPStatusError as e:
                # Another worker may have created the same tag concurrently -
                # re-fetch by name instead of failing outright.
                if e.response.status_code == 400:
                    response = client.get(
                        tags_endpoint,
                        headers=self.headers,
                        params={"name__iexact": tag_name}
                    )
                    response.raise_for_status()
                    results = response.json().get("results", [])
                    if results:
                        return results[0]["id"]
                raise

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
        
        This is a convenience method that extracts patient name, date, hospital,
        and report type from a medical info dictionary (e.g., from MedicalInfo schema).
        
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

        report_type = hospital_info.get("report_type")

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
            tag_ids=tag_ids,
            report_type=report_type
        )
