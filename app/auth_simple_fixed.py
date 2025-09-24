"""
Simplified authentication for frontend routes - FIXED VERSION
"""

from fastapi import Request
from fastapi.responses import RedirectResponse
from typing import Optional
import os
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production-123456789")
ALGORITHM = "HS256"


def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None


def check_auth(request: Request) -> Optional[dict]:
    """Check if user is authenticated from cookie."""
    # Get token from cookie
    token = request.cookies.get("access_token")

    if not token:
        return None

    # Handle quoted cookie values
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]

    # Handle Bearer prefix
    if token.startswith("Bearer "):
        token = token[7:]

    # Decode and validate token
    try:
        user_data = decode_token(token)
        if user_data and user_data.get('sub'):
            return user_data
    except Exception:
        pass

    return None


def require_auth(request: Request):
    """Require authentication or redirect to login."""
    user_data = check_auth(request)
    if not user_data:
        current_path = str(request.url.path)
        return RedirectResponse(
            url=f"/auth/login?next={current_path}",
            status_code=302
        )
    return user_data