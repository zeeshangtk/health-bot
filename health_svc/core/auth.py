"""
Authentication module for Health Service API.

Provides API key authentication for securing endpoints.
"""
import logging
import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from core.config import API_KEY

logger = logging.getLogger(__name__)

# Header name for API key authentication
API_KEY_HEADER_NAME = "X-API-Key"

# Create the API key header security scheme
api_key_header = APIKeyHeader(
    name=API_KEY_HEADER_NAME,
    auto_error=False,  # We'll handle the error ourselves for better messages
    description="API key for authenticating requests. Include in the X-API-Key header.",
)


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> str:
    """
    Verify the API key from the request header.
    
    This dependency should be used on all protected endpoints.
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        api_key: The API key from the X-API-Key header.
        
    Returns:
        str: The validated API key.
        
    Raises:
        HTTPException: 401 Unauthorized if key is missing.
        HTTPException: 403 Forbidden if key is invalid.
    """
    if api_key is None:
        logger.warning("API request without authentication header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, API_KEY):
        logger.warning("API request with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key

