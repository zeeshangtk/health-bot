"""
Service for extracting structured data from medical laboratory reports using Google Gemini AI.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any

import google.generativeai as genai
from PIL import Image

from core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for extracting structured data from medical reports using Gemini AI."""
    
    def __init__(self, api_key: str | None = None):
        """
        Initialize the Gemini service.
        
        Args:
            api_key: Google Gemini API key. If not provided, loads from settings.
            
        Raises:
            ValueError: If API key is not provided.
        """
        self.api_key = api_key or settings.gemini_api_key
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
        self.user_prompt = """
You are an advanced medical data extraction engine powered by OCR and structured parsing.

Your task is to analyze the uploaded medical laboratory report image(s), extract ALL visible and readable information, and convert it into a single, valid JSON object. Handle multi-page reports by combining data across pages without duplication.

==============================
1. OUTPUT FORMAT (MANDATORY)
==============================
- Output MUST be a single, valid JSON object with no leading or trailing whitespace.
- Output MUST start immediately with '{' and end with '}'.
- Do NOT include any markdown, code fences, comments, explanations, preambles, summaries, or extra text outside the JSON.
- Do NOT hallucinate, infer, or fabricate any data—extract only what is explicitly visible and legible in the image.
- If the image is blurry, rotated, or partially illegible, extract only the clear parts and use null for unreadable fields.

==============================
2. JSON SCHEMA (STRICT)
==============================
Adhere exactly to this schema. All top-level keys are required; include them even if empty. Do not add extra keys.

{
  "hospital_info": {
    "name": string | null,
    "report_type": string | null
  },
  "patient_info": {
    "name": string | null,
    "id": string | null,
    "age": string | null,
    "sex": string | null,
    "sample_date": string | null,
    "referring_doctor": string | null
  },
  "biochemistry_results": {
    "CATEGORY_NAME": [
      {
        "test_name": string,
        "results": string | null,
        "unit": string | null,
        "reference_range": string | null,
        "flag": string | null
      }
    ]
  }
}

- If no tests in a category, use an empty array: [].
- If no biochemistry results at all, use an empty object: {}.

==============================
3. DATA EXTRACTION RULES
==============================
- Extract ONLY visible text and data from the image. Ignore logos, watermarks, or non-text elements.
- For tables: Parse row-by-row, associating tests with their results, units, ranges, and flags.
- Handle multiple sections or tables by merging into the appropriate categories.
- If data is duplicated (e.g., across pages), extract once using the clearest version.
- If text is cut off or overlapped, use null for incomplete fields.

NUMBERS AND RESULTS:
- Extract all values as STRINGS to preserve exact formatting (e.g., "7.00", "<5", "Negative").
- Do not convert or round; keep leading/trailing zeros and symbols.

DATES:
- Format 'sample_date' strictly as: "DD-MM-YYYY HH:MM AM/PM"
  Example: "27-12-2025 10:30 AM"
- Normalize variations: "Dec 27, 2025 10:30 AM" → "27-12-2025 10:30 AM"
- If time is missing, use date only: "27-12-2025"
- If date is unreadable, use null.

REFERENCE RANGES:
- Normalize to 'min-max' string format:
  - "<200" → "0-200"
  - ">40" → "40-9999"
  - "Normal: 10-50" → "10-50"
  - Age/sex-specific: Concatenate if multiple, e.g., "Male: 10-50; Female: 8-45"
- If no range is shown, use null.

FLAGS:
- Extract exactly as shown (e.g., "H", "L", "High", "Low", "Abnormal", "*").
- If not present, use null.

==============================
4. TEST NORMALIZATION
==============================
Group tests under these predefined category keys (uppercase with underscores). Map variations/abbreviations to the canonical test_name. Case-insensitive matching.

KIDNEY_FUNCTION:
- Creatinine (Serum Creatinine, Creat, Cr)
- Blood Urea (Serum Urea, Urea)
- Blood Urea Nitrogen (BUN)
- Uric Acid (Serum Uric Acid, UA)

ELECTROLYTES:
- Sodium (Serum Sodium, Na+, Na)
- Potassium (Serum Potassium, K+, K)
- Chloride (Serum Chloride, Cl-, Cl)
- Calcium (Serum Calcium, Ca++, Ca)
- Phosphorus (Serum Phosphorus, P)
- Magnesium (Serum Magnesium, Mg)

LIVER_FUNCTION:
- AST (SGOT) (Aspartate Aminotransferase, AST, SGOT)
- ALT (SGPT) (Alanine Aminotransferase, ALT, SGPT)
- Alkaline Phosphatase (ALP, Alk Phos)
- Total Bilirubin (T. Bilirubin, TBIL)
- Direct Bilirubin (D. Bilirubin, DBIL)
- Indirect Bilirubin (I. Bilirubin, IBIL)
- Albumin (Serum Albumin, Alb)
- Total Protein (T. Protein, TP)
- GGT (Gamma GT, Gamma-Glutamyl Transferase, GGTP)

LIPID_PROFILE:
- Total Cholesterol (Chol, TC)
- HDL Cholesterol (HDL-C, HDL)
- LDL Cholesterol (LDL-C, LDL)
- VLDL Cholesterol (VLDL)
- Triglycerides (TG, Trig)

DIABETES:
- Fasting Blood Sugar (FBS, Fasting Glucose, FBG)
- Random Blood Sugar (RBS, Random Glucose, RBG)
- Post Prandial Blood Sugar (PPBS, PP Blood Sugar, PPBG)
- HbA1c (Glycated Hemoglobin, Glycosylated Hemoglobin, A1C)

HEMATOLOGY:
- Haemoglobin (Hemoglobin, Hb, Hgb)
- Total Leucocyte Count (TLC, WBC Count, WBC)
- Platelet Count (PLT, Platelets)
- RBC Count (RBC, Red Blood Cells)
- Hematocrit (HCT, PCV)
- ESR (Erythrocyte Sedimentation Rate)

THYROID:
- TSH (Thyroid Stimulating Hormone)
- T3 (Triiodothyronine, Total T3)
- T4 (Thyroxine, Total T4)
- Free T3 (FT3)
- Free T4 (FT4)

OTHER:
- Place any test not matching above categories here. Use original name if no canonical match.

- If a test fits multiple categories, prioritize the most specific.
- Preserve order of tests within categories as they appear in the report.

==============================
5. FINAL VALIDATION
==============================
Before responding:
- Ensure JSON syntax is valid and parseable.
- Ensure all required top-level keys exist: hospital_info, patient_info, biochemistry_results.
- Ensure no extra keys are added beyond the schema.
- Ensure output contains ONLY raw JSON—no wrappers, acknowledgments, or explanations.
"""
    
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
            file_path: Path to the image file containing the lab report.
            
        Returns:
            dict: A dictionary with keys 'hospital_info', 'patient_info', and 'results'
                matching the LabReport Pydantic model structure.
                
        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the response cannot be parsed or is invalid.
            Exception: For other API or processing errors.
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
            logger.info(f"Gemini response: {response_text}")
            # Robust JSON extraction: Find the First '{' and Last '}'
            # This handles cases where Gemini adds conversational text or markdown code blocks
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            
            if start_index != -1 and end_index != -1:
                response_text = response_text[start_index : end_index + 1]
            else:
                logger.warning("Could not find JSON object in Gemini response")
            
            logger.info(f"Gemini response: {response_text}")
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
            extracted_data: Raw data from Gemini API with biochemistry_results as dict.
            
        Returns:
            dict: Transformed data matching LabReport.model_dump() structure.
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
