from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.exceptions.base import AuthenticationException, TokenExpiredException
from src.utils.jwt_utils import decode_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentActor:
    actor_id:      str
    role:          str
    email:         Optional[str]
    company_id:    Optional[str]
    product_tiers: Optional[dict]


async def get_current_actor(
    request:     Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentActor:
    token: Optional[str] = None

    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
    except TokenExpiredException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required.",
        )

    return CurrentActor(
        actor_id=str(payload["sub"]),
        role=payload["role"],
        email=payload.get("email"),
        company_id=payload.get("company_id"),
        product_tiers=payload.get("product_tiers"),
    )


def require_roles(*roles: str):
    async def _guard(
        actor: CurrentActor = Depends(get_current_actor),
    ) -> CurrentActor:
        if actor.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}.",
            )
        return actor
    return _guard


# ── keep old name working if anything imports it ──────────────────────────────
require_role = require_roles