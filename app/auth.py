"""
Authentication and authorization module for the consultant matching system.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
import os
import secrets

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production-123456789")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for API endpoints
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


class UserRole:
    """User role constants"""
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: str  # Changed from EmailStr to str
    password: str
    full_name: str
    role: str = UserRole.VIEWER
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[str] = None  # Changed from EmailStr to str
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserInDB(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    hashed_password: str
    created_at: datetime
    last_login: Optional[datetime] = None


class User(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # If the hash format is not recognized, try to rehash
        print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        if username is None:
            return None
        return TokenData(username=username, user_id=user_id, role=role)
    except JWTError:
        return None


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """Get the current authenticated user from JWT token or session."""
    # Try to get user from session (for web UI)
    if hasattr(request.state, "user"):
        return request.state.user
    
    # Try to get user from JWT token (for API)
    if not token:
        # Check for token in cookies (for web UI)
        token = request.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token[7:]  # Remove "Bearer " prefix
    
    if not token:
        return None
    
    token_data = decode_token(token)
    if not token_data:
        return None
    
    # Here you would typically fetch the user from database
    # For now, we'll return a mock user based on token data
    from app.repo import DatabaseRepository
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/consultant_matching")
    
    try:
        db = DatabaseRepository(db_url)
        await db.init()
        user = await db.get_user_by_username(token_data.username)
        await db.close()
        
        if user and user.is_active:
            return user
    except:
        pass
    
    return None


async def require_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require an authenticated user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


async def require_role(allowed_roles: list[str]):
    """Require specific user roles."""
    async def role_checker(current_user: User = Depends(require_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


async def require_admin(current_user: User = Depends(require_user)) -> User:
    """Require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_user_from_cookie(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from cookie for HTML frontend routes. Returns dict or redirects to login."""
    # Try to get token from cookie
    token = request.cookies.get("access_token")
    if not token:
        return None

    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    # Decode token
    token_data = decode_token(token)
    if not token_data:
        return None

    # Return user data as dict for template rendering
    return {
        "username": token_data.username,
        "user_id": token_data.user_id,
        "role": token_data.role
    }


def require_auth_cookie(request: Request) -> Dict[str, Any]:
    """Synchronous function to check auth and redirect if not authenticated."""
    import asyncio

    # Try to get token from cookie
    token = request.cookies.get("access_token")
    if not token:
        # Redirect to login with next parameter
        next_url = str(request.url.path)
        if request.url.query:
            next_url += f"?{request.url.query}"
        return RedirectResponse(
            url=f"/auth/login?next={next_url}",
            status_code=303
        )

    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    # Decode token
    token_data = decode_token(token)
    if not token_data:
        # Invalid token - redirect to login
        next_url = str(request.url.path)
        return RedirectResponse(
            url=f"/auth/login?next={next_url}",
            status_code=303
        )

    # Return user data as dict
    return {
        "username": token_data.username,
        "user_id": token_data.user_id,
        "role": token_data.role
    }


class AuthMiddleware:
    """Middleware to check authentication for web routes."""
    
    def __init__(self, protected_paths: list[str] = None):
        self.protected_paths = protected_paths or [
            "/consultant/",
            "/api/",
        ]
    
    async def __call__(self, request: Request, call_next):
        """Check if the request path requires authentication."""
        path = request.url.path
        
        # Skip authentication for login page and auth endpoints
        if path in ["/auth/login", "/auth/token", "/auth/logout"] or path.startswith("/auth/"):
            return await call_next(request)
        
        # Check if path requires authentication
        requires_auth = any(path.startswith(p) for p in self.protected_paths)
        
        if requires_auth:
            # Try to get token from cookie
            token = request.cookies.get("access_token")
            if token and token.startswith("Bearer "):
                token = token[7:]
            
            if not token:
                # Redirect to login page for web requests
                if not path.startswith("/api/"):
                    return RedirectResponse(url="/auth/login?next=" + path, status_code=302)
                # Return 401 for API requests
                return HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            # Validate token
            token_data = decode_token(token)
            if not token_data:
                if not path.startswith("/api/"):
                    return RedirectResponse(url="/auth/login?next=" + path, status_code=302)
                return HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
            
            # Store user info in request state
            request.state.username = token_data.username
            request.state.user_id = token_data.user_id
            request.state.role = token_data.role
        
        response = await call_next(request)
        return response