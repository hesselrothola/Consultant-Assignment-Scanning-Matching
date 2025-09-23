"""
Simplified authentication for frontend routes.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from typing import Optional
import os
import secrets
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production-123456789")
ALGORITHM = "HS256"


def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (JWTError, Exception):
        return None


def check_auth(request: Request) -> Optional[dict]:
    """Check if user is authenticated from cookie."""
    # Get token from cookie
    token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    # Remove quotes if present (cookie values might be quoted)
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    # Decode token
    user_data = decode_token(token)
    return user_data


def require_auth(request: Request):
    """Require authentication or redirect to login."""
    user_data = check_auth(request)
    if not user_data:
        # Get the current path for redirect after login
        current_path = str(request.url.path)
        return RedirectResponse(
            url=f"/auth/login?next={current_path}",
            status_code=302
        )
    return user_data