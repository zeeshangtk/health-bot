"""
Health router - root endpoint and health checks.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["Health"])
async def root():
    """
    Root endpoint.
    
    Returns basic API information including service name and version.
    Use this endpoint to verify the API is running and accessible.
    """
    return {"message": "Health Service API", "version": "1.0.0"}

