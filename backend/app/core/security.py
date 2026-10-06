"""Auth adapter.

AUTH_MODE=mock     -> fixed local user (blocked in production by config guard)
AUTH_MODE=supabase -> verifies Supabase JWTs. Asymmetric signing keys are
                      verified via the project's JWKS endpoint; legacy HS256
                      projects fall back to SUPABASE_JWT_SECRET.

This is a sync dependency on purpose: FastAPI runs it in a threadpool, so the
(cached) JWKS fetch never blocks the event loop. Tokens are never logged.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import AuthMode, Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_ALLOWED_ALGORITHMS = {"HS256", "RS256", "ES256"}


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str
    is_mock: bool = False


@lru_cache
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_keys=True)


def _decode_supabase_token(token: str, settings: Settings) -> dict[str, Any]:
    algorithm = jwt.get_unverified_header(token).get("alg", "")
    if algorithm not in _ALLOWED_ALGORITHMS:
        raise jwt.InvalidAlgorithmError("Unsupported token algorithm")
    if algorithm == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError("HS256 token received but SUPABASE_JWT_SECRET is not set")
        key: Any = settings.supabase_jwt_secret
    else:
        key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        key=key,
        algorithms=[algorithm],
        audience="authenticated",
        issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    if settings.auth_mode is AuthMode.MOCK:
        return CurrentUser(id=settings.mock_user_id, role="citizen", is_mock=True)

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    try:
        claims = _decode_supabase_token(credentials.credentials, settings)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.") from exc

    role = str(claims.get("app_metadata", {}).get("role", "citizen"))
    return CurrentUser(id=str(claims["sub"]), role=role)
