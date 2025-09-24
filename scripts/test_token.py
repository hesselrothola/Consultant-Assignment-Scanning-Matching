#!/usr/bin/env python3
"""
Test token decoding with the same logic as auth_simple.py
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

def test_token():
    # Test token from the login response
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiJiNGEzYjI5NS04MDM2LTRmZGYtOTcxMS03YzE3YjkyYzJjYTMiLCJyb2xlIjoiYWRtaW4iLCJleHAiOjE3NTg3MjA5MTEsInR5cGUiOiJhY2Nlc3MifQ.HE7ViGp3UOUk2zR0L6oYNubikRiuPWfxVMuJm-g36ik"

    print("Testing token decode...")
    result = decode_token(token)

    if result:
        print(f"✓ Token decoded successfully!")
        print(f"User: {result.get('sub')}")
        print(f"User ID: {result.get('user_id')}")
        print(f"Role: {result.get('role')}")
        print(f"Expires: {result.get('exp')}")
    else:
        print("✗ Token decode failed")

if __name__ == "__main__":
    test_token()