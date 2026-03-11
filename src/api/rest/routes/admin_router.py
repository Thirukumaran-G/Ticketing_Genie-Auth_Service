from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import CurrentActor, require_roles
from src.core.services.admin_service import AdminService
from src.data.clients.postgres_client import get_db_session
from src.schemas.admin_schemas import (
    AdminUserResponse,
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    SubscriptionAssignRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    TierResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


def _svc(session: AsyncSession = Depends(get_db_session)) -> AdminService:
    return AdminService(session)


# ── Companies ─────────────────────────────────────────────────────────────────

@router.post(
    "/companies",
    response_model=CompanyResponse,
    status_code=201,
    summary="Create company",
)
async def create_company(
    payload: CompanyCreateRequest,
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> CompanyResponse:
    return await service.create_company(payload, actor.actor_id)


@router.get(
    "/companies",
    response_model=List[CompanyResponse],
    summary="List all companies",
)
async def list_companies(
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> List[CompanyResponse]:
    return await service.list_companies()


@router.get(
    "/companies/{company_id}",
    response_model=CompanyResponse,
    summary="Get company by ID",
)
async def get_company(
    company_id: uuid.UUID,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> CompanyResponse:
    return await service.get_company(company_id)


@router.patch(
    "/companies/{company_id}",
    response_model=CompanyResponse,
    summary="Update company name / domain / active status",
)
async def update_company(
    company_id: uuid.UUID,
    payload:    CompanyUpdateRequest,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> CompanyResponse:
    return await service.update_company(company_id, payload)


# ── Products ──────────────────────────────────────────────────────────────────

@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    summary="Create product",
)
async def create_product(
    payload: ProductCreateRequest,
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> ProductResponse:
    return await service.create_product(payload, actor.actor_id)


@router.get(
    "/products",
    response_model=List[ProductResponse],
    summary="List all products",
)
async def list_products(
    service: AdminService = Depends(_svc),
) -> List[ProductResponse]:
    return await service.list_products()


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product name or deactivate",
)
async def update_product(
    product_id: uuid.UUID,
    payload:    ProductUpdateRequest,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> ProductResponse:
    return await service.update_product(product_id, payload)


# ── Subscriptions ─────────────────────────────────────────────────────────────

@router.post(
    "/companies/{company_id}/subscriptions",
    response_model=SubscriptionResponse,
    status_code=201,
    summary="Assign product + tier to company",
)
async def assign_subscription(
    company_id: uuid.UUID,
    payload:    SubscriptionAssignRequest,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> SubscriptionResponse:
    return await service.assign_subscription(company_id, payload, actor.actor_id)


@router.get(
    "/companies/{company_id}/subscriptions",
    response_model=List[SubscriptionResponse],
    summary="List subscriptions for a company",
)
async def list_subscriptions(
    company_id: uuid.UUID,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> List[SubscriptionResponse]:
    return await service.list_subscriptions(company_id)


@router.patch(
    "/companies/{company_id}/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update subscription tier or deactivate",
)
async def update_subscription(
    company_id:      uuid.UUID,
    subscription_id: uuid.UUID,
    payload:         SubscriptionUpdateRequest,
    actor:           CurrentActor = Depends(require_roles("admin")),
    service:         AdminService = Depends(_svc),
) -> SubscriptionResponse:
    return await service.update_subscription(
        company_id, subscription_id, payload, actor.actor_id
    )


# ── Tiers ─────────────────────────────────────────────────────────────────────

@router.get(
    "/tiers",
    response_model=List[TierResponse],
    summary="List available tiers",
)
async def list_tiers(
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> List[TierResponse]:
    return await service.list_tiers()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=List[AdminUserResponse],
    summary="List all users",
)
async def list_users(
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> List[AdminUserResponse]:
    return await service.list_users()


@router.patch(
    "/users/{user_id}/deactivate",
    status_code=204,
    summary="Deactivate a user",
)
async def deactivate_user(
    user_id: uuid.UUID,
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> Response:
    await service.deactivate_user(user_id)
    return Response(status_code=204)