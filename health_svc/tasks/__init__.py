"""
Celery tasks module.
"""
from .upload_tasks import process_uploaded_file

__all__ = ["process_uploaded_file"]

