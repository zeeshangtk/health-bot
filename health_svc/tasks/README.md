# Upload Tasks

This module contains Celery tasks for processing uploaded files asynchronously.

## Overview

The `upload_tasks.py` module provides background task processing for files uploaded to the health service. Files are processed asynchronously after being successfully saved to disk.

## Current Functionality

### Database Storage

Currently, the task processes JSON data extracted from uploaded files and stores the information in the database by looping over a JSON array with the following structure:

```json
{
  "hospital_info": {
    "hospital_name": "VR John Doe",
    "report_type": "Laboratory Reports"
  },
  "patient_info": {
    "patient_name": "Mrs Test Patient",
    "patient_id": "ABB17985",
    "age_sex": "63Y / FEMALE",
    "sample_date": "08-11-2025 03:17 PM",
    "referring_doctor_full_name_titles": "DR. John Doe MBBS, MD GENERAL MEDICINE, DNB CARDIOLOGY"
  },
  "results":  [
      {
        "test_name": "Blood Urea",
        "results": "64.0",
        "unit": "mg/dl",
        "reference_range": "10.0-40.0"
      },
      {
        "test_name": "Random Blood Sugar",
        "results": "160.7",
        "unit": "mg/dl",
        "reference_range": "70.0-130.0"
      },
      {
        "test_name": "Creatinine",
        "results": "1.6",
        "unit": "mg/dl",
        "reference_range": "0.8-1.2"
      },
      {
        "test_name": "Blood Urea Nitrogen",
        "results": "29.9",
        "unit": "mg/dl",
        "reference_range": "7.0-20.0"
      },
      {
        "test_name": "Calcium",
        "results": "9.5",
        "unit": "mg/dl",
        "reference_range": "8.4-11.0"
      },
      {
        "test_name": "Uric Acid",
        "results": "3.6",
        "unit": "mg/dl",
        "reference_range": "2.7-6.5"
      },
      {
        "test_name": "Sodium",
        "results": "143.3",
        "unit": "mMol/L",
        "reference_range": "136.0-145.0"
      },
      {
        "test_name": "Potassium",
        "results": "5.09",
        "unit": "mMol/L",
        "reference_range": "3.5-5.1"
      },
      {
        "test_name": "Chloride",
        "results": "100.3",
        "unit": "mMol/L",
        "reference_range": "97.0-108.0"
      },
      {
        "test_name": "Urine Micro Albuminuria",
        "results": "↑250.0",
        "unit": "mg/l",
        "reference_range": "1.0-20.0"
      }
    ]
  }
```

The task processes this structure by:
1. Extracting hospital information from `hospital_info`
2. Extracting patient information from `patient_info`
3. Iterating through all test categories in `biochemistry_results`
4. For each test category, looping through individual test results
5. Storing each test result as a separate health record in the database

## Future Enhancements

### Gemini API Integration

In the future, this module will integrate with the **Google Gemini API** to:
- Extract structured data from medical report images (OCR and data extraction)
- Parse laboratory reports and convert them to the standardized JSON format
- Validate extracted data against expected schemas
- Provide intelligent data extraction from various report formats

The Gemini API integration will enable automatic processing of uploaded medical report images, eliminating the need for manual JSON input and making the system more user-friendly.

## Task Details

### `process_uploaded_file`

**Signature:**
```python
@celery_app.task(bind=True, max_retries=3)
def process_uploaded_file(self, filename, file_path, file_size, content_type, upload_timestamp)
```

**Parameters:**
- `filename`: Unique filename of the uploaded file
- `file_path`: Full path to the stored file
- `file_size`: Size of the file in bytes
- `content_type`: MIME type of the file
- `upload_timestamp`: ISO format timestamp of upload

**Returns:**
- `dict`: Processing result with status and metadata

**Error Handling:**
- Retries up to 3 times with exponential backoff for transient errors
- Does not retry on `FileNotFoundError` (file doesn't exist)
- Logs all errors with full exception information

## Usage

The task is automatically queued by the `UploadService` after a file is successfully uploaded. It runs asynchronously in the background using Celery workers.

## Dependencies

- `celery`: For asynchronous task processing
- `pathlib`: For file path operations
- `datetime`: For timestamp handling
- `logging`: For error and info logging

