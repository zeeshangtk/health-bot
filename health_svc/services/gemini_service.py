"""
Service for extracting structured data from medical laboratory reports using Google Gemini AI.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

import google.generativeai as genai
from PIL import Image

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for extracting structured data from medical reports using Gemini AI."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini service.
        
        Args:
            api_key: Google Gemini API key. If not provided, loads from GEMINI_API_KEY env var.
            
        Raises:
            ValueError: If API key is not provided and not found in environment.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Set it or pass api_key parameter."
            )
        
        # Configure the Gemini client
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-flash-latest')
        
        # Define the extraction prompt
        self.user_prompt = (
            "Analyze the uploaded medical laboratory report image and extract its data "
            "into a JSON object with the top-level keys: 'hospital_info', "
            "'patient_info', and 'biochemistry_results'.\n\n"
            "1. 'hospital_info': Include the hospital name and report type.\n"
            "2. 'patient_info': Include patient name, ID, age/sex, sample date, and the "
            "full name and titles of the referring doctor.\n"
            "3. 'biochemistry_results': Provide a dictionary grouping tests into major "
            "categories (e.g., KIDNEY_FUNCTION_TEST, ELECTROLYTES, OTHER_TEST). Each "
            "test entry must contain: 'test_name', 'results', 'unit', and "
            "'reference_range' (use 'min-max' format when possible)."
        )
    
    def extract_lab_report(self, file_path: str) -> Dict[str, Any]:
        """
        Extract structured data from a medical laboratory report image.
        
        This method:
        1. Loads the image file from the provided path
        2. Sends it to Gemini AI with the extraction prompt
        3. Parses the JSON response
        4. Transforms the response to match the LabReport structure
        5. Returns a dictionary matching LabReport.model_dump() format
        
        Args:
            file_path: Path to the image file containing the lab report
            
        Returns:
            dict: A dictionary with keys 'hospital_info', 'patient_info', and 'results'
                matching the LabReport Pydantic model structure.
                
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the response cannot be parsed or is invalid
            Exception: For other API or processing errors
        """
        file_path_obj = Path(file_path)
        
        # Verify file exists
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Load the image file
            logger.info(f"Sending image to Gemini for extraction: {file_path}")
            
            # Open image using PIL
            image = Image.open(file_path_obj)
            
            # Generate content with the image and prompt
            response = self.model.generate_content([self.user_prompt, image])
            
            # Extract text from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            elif response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove trailing ```
            
            response_text = response_text.strip()
            
            # Parse JSON response
            try:
                extracted_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {response_text[:200]}")
                raise ValueError(f"Invalid JSON response from Gemini: {str(e)}") from e
            
            # Transform the response to match LabReport structure
            # Gemini returns biochemistry_results as a dict, but LabReport expects results as a list
            lab_report = self._transform_to_lab_report_format(extracted_data)
            
            logger.info(f"Successfully extracted lab report data from: {file_path}")
            return lab_report
            
        except FileNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Error extracting lab report from {file_path}: {str(e)}",
                exc_info=True
            )
            raise
    
    def _transform_to_lab_report_format(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Gemini response to match LabReport Pydantic model structure.
        
        Converts biochemistry_results (dict of categories) into a flat results list.
        
        Args:
            extracted_data: Raw data from Gemini API with biochemistry_results as dict
            
        Returns:
            dict: Transformed data matching LabReport.model_dump() structure
        """
        # Extract the three main sections
        hospital_info = extracted_data.get("hospital_info", {})
        patient_info = extracted_data.get("patient_info", {})
        biochemistry_results = extracted_data.get("biochemistry_results", {})
        
        # Flatten biochemistry_results dict into a single list
        results = []
        for category, test_list in biochemistry_results.items():
            if isinstance(test_list, list):
                results.extend(test_list)
            else:
                # Handle case where category value might not be a list
                logger.warning(f"Unexpected format for category {category}: {test_list}")
        
        # Return in LabReport format
        return {
            "hospital_info": hospital_info,
            "patient_info": patient_info,
            "results": results
        }

