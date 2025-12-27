import httpx
import os
import sys

def test_upload_with_patient():
    url = "http://localhost:8000/api/v1/records/upload"
    patient_name = "Mrs Nazra Mastoor"
    
    # Create a dummy image file
    with open("test_upload.jpg", "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0" + b"\x00" * 1024)
    
    files = {
        "file": ("test_upload.jpg", open("test_upload.jpg", "rb"), "image/jpeg")
    }
    data = {
        "patient": patient_name
    }
    
    print(f"Uploading file with patient: {patient_name}")
    try:
        response = httpx.post(url, files=files, data=data, timeout=30.0)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists("test_upload.jpg"):
            os.remove("test_upload.jpg")

if __name__ == "__main__":
    test_upload_with_patient()
