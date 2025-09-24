#!/usr/bin/env python3
"""
Debug authentication by checking cookie parsing
"""

import os
from jose import JWTError, jwt

SECRET_KEY = "your-secret-key-here-change-in-production-123456789"
ALGORITHM = "HS256"

def decode_token(token: str):
    """Decode JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (JWTError, Exception) as e:
        print(f"Token decode error: {e}")
        return None

def test_cookie_parsing():
    # Simulate the cookie value that would be set by the server
    cookie_value = '"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiJiNGEzYjI5NS04MDM2LTRmZGYtOTcxMS03YzE3YjkyYzJjYTMiLCJyb2xlIjoiYWRtaW4iLCJleHAiOjE3NTg3MjA5MTEsInR5cGUiOiJhY2Nlc3MifQ.HE7ViGp3UOUk2zR0L6oYNubikRiuPWfxVMuJm-g36ik"'

    print(f"Original cookie: {cookie_value}")

    # Parse like auth_simple.py does
    token = cookie_value

    # Remove quotes if present (cookie values might be quoted)
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]
        print(f"After quote removal: {token}")

    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
        print(f"After Bearer removal: {token}")

    # Decode token
    user_data = decode_token(token)
    if user_data:
        print(f"✓ Authentication successful!")
        print(f"User: {user_data.get('sub')}")
        print(f"Role: {user_data.get('role')}")
        return user_data
    else:
        print("✗ Authentication failed!")
        return None

if __name__ == "__main__":
    test_cookie_parsing()