"""
Simplified authentication for frontend routes with debug logging.
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
        print(f"DEBUG: Token decoded successfully: {payload}")
        return payload
    except (JWTError, Exception) as e:
        print(f"DEBUG: Token decode failed: {e}")
        return None


def check_auth(request: Request) -> Optional[dict]:
    """Check if user is authenticated from cookie."""
    # Get token from cookie
    token = request.cookies.get("access_token")
    print(f"DEBUG: Raw cookie value: {token}")

    if not token:
        print("DEBUG: No access_token cookie found")
        return None

    # Remove quotes if present (cookie values might be quoted)
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]
        print(f"DEBUG: After quote removal: {token}")

    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
        print(f"DEBUG: After Bearer removal: {token}")

    # Decode token
    user_data = decode_token(token)
    print(f"DEBUG: Final user_data: {user_data}")
    return user_data


def require_auth(request: Request):
    """Require authentication or redirect to login."""
    print(f"DEBUG: Checking auth for path: {request.url.path}")
    user_data = check_auth(request)
    if not user_data:
        print("DEBUG: Auth failed, redirecting to login")
        # Get the current path for redirect after login
        current_path = str(request.url.path)
        return RedirectResponse(
            url=f"/auth/login?next={current_path}",
            status_code=302
        )
    print(f"DEBUG: Auth successful for user: {user_data.get('sub')}")
    return user_data