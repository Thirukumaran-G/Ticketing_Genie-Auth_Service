from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel as _BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.auth_service import AuthService
from src.core.services.internal_service import InternalAuthService
from src.data.clients.postgres_client import get_db_session, get_fresh_read_session
from src.schemas.auth_schemas import (
    CompanyByDomainResponse,
    InternalCustomerCreateRequest,
    InternalCustomerCreateResponse,
    InternalUserCreateRequest,
    InternalUserCreateResponse,
    PreferredContactUpdate,
    ProductListResponse,
    UserEmailResponse,
)


class TierLookupResponse(_BaseModel):
    tier_id:   str
    tier_name: str


router = APIRouter(prefix="/internal", tags=["Internal"])


# ── Dependency factories ───────────────────────────────────────────────────────

def _get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(session)


def _get_internal_service(
    session: AsyncSession = Depends(get_db_session),
) -> InternalAuthService:
    return InternalAuthService(session)


def _get_internal_read_service(
    session: AsyncSession = Depends(get_fresh_read_session),
) -> InternalAuthService:
    return InternalAuthService(session)


# ── User routes ────────────────────────────────────────────────────────────────

@router.post(
    "/users",
    response_model=InternalUserCreateResponse,
    status_code=201,
    include_in_schema=False,
)
async def internal_create_user(
    payload: InternalUserCreateRequest,
    service: AuthService = Depends(_get_auth_service),
) -> InternalUserCreateResponse:
    return await service.internal_create_user(payload)


@router.get("/users/{user_id}", include_in_schema=False)
async def get_user_internal(
    user_id: str,
    service: InternalAuthService = Depends(_get_internal_service),
) -> dict[str, Any]:
    return await service.get_user_with_role(user_id)


@router.get(
    "/users/{user_id}/email",
    response_model=UserEmailResponse,
    include_in_schema=False,
)
async def internal_get_user_email(
    user_id: uuid.UUID,
    service: AuthService = Depends(_get_auth_service),
) -> dict[str,Any]:
    return await service.get_user_email(str(user_id))


@router.patch(
    "/users/{user_id}/preferred-contact",
    status_code=204,
    include_in_schema=False,
)
async def internal_set_preferred_contact(
    user_id: uuid.UUID,
    payload: PreferredContactUpdate,
    service: InternalAuthService = Depends(_get_internal_service),
) -> Response:
    await service.set_preferred_contact(user_id, payload)
    return Response(status_code=204)


# ── Tier routes ────────────────────────────────────────────────────────────────

@router.get(
    "/tiers/by-name/{tier_name}",
    response_model=TierLookupResponse,
    include_in_schema=False,
)
async def internal_get_tier_by_name(
    tier_name: str,
    service: InternalAuthService = Depends(_get_internal_service),
) -> TierLookupResponse:
    result = await service.get_tier_by_name(tier_name)
    return TierLookupResponse(**result)


@router.get(
    "/customers/{user_id}/tier",
    response_model=TierLookupResponse,
    include_in_schema=False,
)
async def internal_get_customer_tier(
    user_id: uuid.UUID,
    product_id: uuid.UUID | None = None,
    service: InternalAuthService = Depends(_get_internal_service),
) -> TierLookupResponse:
    result = await service.get_customer_tier(user_id, product_id)
    return TierLookupResponse(**result)


# ── Company routes ─────────────────────────────────────────────────────────────

@router.get(
    "/companies/by-domain/{domain}",
    response_model=CompanyByDomainResponse,
    include_in_schema=False,
)
async def internal_get_company_by_domain(
    domain: str,
    service: InternalAuthService = Depends(_get_internal_read_service),
) -> CompanyByDomainResponse:
    result = await service.get_company_by_domain(domain)
    return CompanyByDomainResponse(**result)


# ── Product routes ─────────────────────────────────────────────────────────────

@router.get(
    "/products/active",
    response_model=ProductListResponse,
    include_in_schema=False,
)
async def internal_list_active_products(
    service: InternalAuthService = Depends(_get_internal_read_service),
) -> ProductListResponse:
    result = await service.list_active_products()
    return ProductListResponse(**result)


# ── Customer routes ────────────────────────────────────────────────────────────

@router.post(
    "/customers/create-or-get",
    response_model=InternalCustomerCreateResponse,
    include_in_schema=False,
)
async def internal_create_or_get_customer(
    payload: InternalCustomerCreateRequest,
    service: InternalAuthService = Depends(_get_internal_service),
) -> InternalCustomerCreateResponse:
    return await service.create_or_get_customer(payload)
