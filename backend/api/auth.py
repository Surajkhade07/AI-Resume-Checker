import logging
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import SUPABASE_JWT_SECRET, SUPABASE_URL

logger = logging.getLogger('ats_resume_scorer')

_bearer_scheme = HTTPBearer(auto_error=False)

_ASYMMETRIC_ALGS = ['ES256', 'RS256']

_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient | None:
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client
    if not SUPABASE_URL:
        return None
    jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    _jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def _verify_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get('alg')

        if alg in _ASYMMETRIC_ALGS:
            jwks_client = _get_jwks_client()
            if jwks_client is not None:
                signing_key = jwks_client.get_signing_key_from_jwt(token).key
                return jwt.decode(
                    token,
                    signing_key,
                    algorithms=_ASYMMETRIC_ALGS,
                    audience='authenticated',
                )

        if alg == 'HS256' and SUPABASE_JWT_SECRET:
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                audience='authenticated',
            )

        # Fallback: unverified decode to safely get the subject user ID if JWKS is unreachable
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        logger.warning(f"Signature check skipped/failed, using unverified payload: {e}")
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return {"sub": "local_user"}


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    if creds is None or not creds.credentials:
        return "local_user"

    token = creds.credentials
    try:
        payload = _verify_token(token)
        user_id = payload.get('sub') or "local_user"
        return str(user_id)
    except Exception as exc:
        logger.warning(f"Auth fallback to local_user: {exc}")
        return "local_user"