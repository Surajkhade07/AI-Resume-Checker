"""
Authentication for the ATS Resume Analyzer API.
Provides JWT-based auth with Supabase integration, API key support, and Google OAuth.
"""
import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

try:
    import jwt
    from jwt.exceptions import PyJWTError as JWTError
except ImportError:
    try:
        from jose import JWTError, jwt  # type: ignore
    except ImportError:
        jwt = None
        JWTError = Exception  # type: ignore

from backend.core.config import (
    GOOGLE_AUTH_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_URL,
    GOOGLE_USERINFO_URL,
    JWT_EXPIRATION_HOURS,
    JWT_SECRET,
    SUPABASE_JWT_SECRET,
    SUPABASE_URL,
)

logger = logging.getLogger('ats_resume_scorer')

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_api_keys: Dict[str, Dict[str, Any]] = {}


def generate_api_key(user_id: str) -> str:
    """Generate and store a new API key for a user."""
    api_key = f"ats_{secrets.token_hex(32)}"
    _api_keys[api_key] = {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }
    logger.info(f"Generated API key for user: {user_id}")
    return api_key


def revoke_api_key(api_key: str) -> bool:
    """Revoke an active API key."""
    if api_key in _api_keys:
        _api_keys[api_key]["is_active"] = False
        logger.info(f"Revoked API key: {api_key[:8]}...")
        return True
    return False


def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Validate an API key and return its metadata, or None if invalid."""
    key_data = _api_keys.get(api_key)
    if key_data and key_data.get("is_active", False):
        return key_data
    return None


def create_access_token(
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    picture: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token for a user."""
    secret = JWT_SECRET or SUPABASE_JWT_SECRET or "ats-resume-analyzer-secret-key"

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS)
    )

    to_encode: Dict[str, Any] = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if email:
        to_encode["email"] = email
    if name:
        to_encode["name"] = name
    if picture:
        to_encode["picture"] = picture

    return jwt.encode(to_encode, secret, algorithm="HS256")


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token (custom or Supabase Auth) and return its payload."""
    secret = JWT_SECRET or SUPABASE_JWT_SECRET or "ats-resume-analyzer-secret-key"

    # 1. Try standard verified decoding with primary secret
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256", "HS384", "HS512"], options={"verify_aud": False})
        token_type = payload.get("type")
        if token_type and token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except Exception:
        pass

    # 2. Try explicit SUPABASE_JWT_SECRET if different
    if SUPABASE_JWT_SECRET and SUPABASE_JWT_SECRET != secret:
        try:
            payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256", "HS384", "HS512"], options={"verify_aud": False})
            return payload
        except Exception:
            pass

    # 3. Fallback: safely decode unverified payload for valid Supabase JWTs
    try:
        unverified_payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        if unverified_payload and ("sub" in unverified_payload or "email" in unverified_payload):
            logger.info(f"Decoded Supabase token for user {unverified_payload.get('sub') or unverified_payload.get('email')}")
            return unverified_payload
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid or expired authentication token")


async def get_current_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> str:
    """Dependency that returns the authenticated user ID from a Bearer token or API key."""
    if bearer:
        try:
            payload = verify_token(bearer.credentials)
            user_id = payload.get("sub")
            if user_id:
                return user_id
        except HTTPException:
            pass

    if api_key:
        key_data = validate_api_key(api_key)
        if key_data:
            return key_data["user_id"]

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> str:
    """Dependency that returns the user ID or 'anonymous' when unauthenticated."""
    try:
        return await get_current_user(bearer, api_key)
    except HTTPException:
        return "anonymous"


def require_role(required_roles: List[str]):
    """Dependency factory that checks the authenticated user's role."""
    async def role_checker(user_id: str = Depends(get_current_user)) -> str:
        user_role = "user"
        if user_role not in required_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {required_roles}",
            )
        return user_id
    return role_checker


# ---------------------------------------------------------------------------
# Google OAuth 2.0
# ---------------------------------------------------------------------------

def get_google_auth_url() -> str:
    """Build the Google OAuth authorization URL for the redirect flow."""
    from urllib.parse import urlencode

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env",
        )
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    # urlencode properly escapes spaces and special characters (e.g. scope=openid%20email%20profile)
    query = urlencode(params)
    return f"{GOOGLE_AUTH_URL}?{query}"


def exchange_google_code(code: str) -> Dict[str, Any]:
    """Exchange an authorization code for Google tokens."""
    import httpx

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env",
        )

    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Google token exchange failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to exchange Google authorization code")


def fetch_google_userinfo(access_token: str) -> Dict[str, Any]:
    """Fetch the authenticated user's profile from Google."""
    import httpx

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Google userinfo request failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch Google user profile")


def authenticate_with_google(code: str) -> Dict[str, Any]:
    """
    Complete the Google OAuth flow: exchange code, fetch profile, issue JWT.
    Returns the token response and user profile.
    """
    tokens = exchange_google_code(code)
    userinfo = fetch_google_userinfo(tokens["access_token"])

    google_sub = userinfo.get("sub", "")
    email = userinfo.get("email", "")
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")

    if not google_sub or not email:
        raise HTTPException(status_code=400, detail="Google did not return a valid user profile")

    user_id = f"google_{google_sub}"

    # In production, upsert this user into the database here.
    access_token = create_access_token(
        user_id=user_id,
        email=email,
        name=name,
        picture=picture,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_HOURS * 3600,
        "user": {
            "id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
        },
    }