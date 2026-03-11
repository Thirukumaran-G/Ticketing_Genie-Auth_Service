### AUTH JWT 

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from src.config.settings import settings
from src.core.exceptions.base import AuthenticationException, TokenExpiredException


def _now() -> datetime:
    return datetime.now(UTC)


def get_scopes_for_role(role_name: str) -> list[str]:
    role_scopes: dict[str, list[str]] = {
        "customer":  ["read:own", "write:own"],
        "agent":     ["read:own", "write:own", "read:tickets", "write:tickets"],
        "team_lead": ["read:own", "write:own", "read:tickets", "write:tickets", "manage:agents"],
        "admin":     ["read:own", "write:own", "read:tickets", "write:tickets", "manage:agents", "manage:all"],
    }
    return role_scopes.get(role_name, ["read:own"])


def create_access_token(
    actor_id:      str,
    role_name:     str,
    email:         Optional[str]                         = None,
    company_id:    Optional[str]                         = None,
    product_tiers: Optional[Dict[str, Any]]              = None,
) -> tuple[str, datetime]:
    """
    JWT payload:
      sub, role, email, jti, iat, exp, type, scopes
      + company_id     → only for customer
      + product_tiers  → only for customer  { "<product_id>": { tier_id, tier_name, code } }
    """
    expire = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti    = str(uuid.uuid4())
    now    = _now()

    payload: dict[str, Any] = {
        "sub":       actor_id,
        "role":      role_name,
        "email":     email,
        "jti":       jti,
        "iat":       now,
        "exp":       expire,
        "type":      "access",
        "scopes":    get_scopes_for_role(role_name),
    }

    # customer-only claims
    if role_name == "customer":
        payload["company_id"]    = company_id
        payload["product_tiers"] = product_tiers or {}

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire


def create_refresh_token(
    actor_id:   str,
    role_name:  str,
    family_id:  Optional[str] = None,
    session_id: Optional[str] = None,
) -> tuple[str, str, str, datetime]:
    """Returns (token_str, jti, session_id, expires_at)."""
    expire = _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti    = str(uuid.uuid4())
    sid    = session_id or str(uuid.uuid4())
    fid    = family_id  or jti

    payload: dict[str, Any] = {
        "sub":        actor_id,
        "role":       role_name,
        "jti":        jti,
        "family_id":  fid,
        "session_id": sid,
        "iat":        _now(),
        "exp":        expire,
        "type":       "refresh",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, sid, expire


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload  # type: ignore[no-any-return]
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredException() from exc
        raise AuthenticationException("Invalid token.") from exc