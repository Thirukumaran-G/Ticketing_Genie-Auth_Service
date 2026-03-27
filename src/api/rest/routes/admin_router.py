from __future__ import annotations

import uuid

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
    RoleResponse,
    SubscriptionAssignRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    TierResponse,
    UserCreateRequest,
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
    response_model=list[CompanyResponse],
    summary="List all companies",
)
async def list_companies(
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> list[CompanyResponse]:
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


@router.delete(
    "/companies/{company_id}",
    status_code=204,
    summary="Hard delete a company",
)
async def delete_company(
    company_id: uuid.UUID,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> Response:
    await service.delete_company(company_id)
    return Response(status_code=204)


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
    response_model=list[ProductResponse],
    summary="List all products",
)
async def list_products(
    service: AdminService = Depends(_svc),
) -> list[ProductResponse]:
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


@router.delete(
    "/products/{product_id}",
    status_code=204,
    summary="Hard delete a product",
)
async def delete_product(
    product_id: uuid.UUID,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> Response:
    await service.delete_product(product_id)
    return Response(status_code=204)


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
    response_model=list[SubscriptionResponse],
    summary="List subscriptions for a company",
)
async def list_subscriptions(
    company_id: uuid.UUID,
    actor:      CurrentActor = Depends(require_roles("admin")),
    service:    AdminService = Depends(_svc),
) -> list[SubscriptionResponse]:
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


@router.delete(
    "/companies/{company_id}/subscriptions/{subscription_id}",
    status_code=204,
    summary="Hard delete a subscription",
)
async def delete_subscription(
    company_id:      uuid.UUID,
    subscription_id: uuid.UUID,
    actor:           CurrentActor = Depends(require_roles("admin")),
    service:         AdminService = Depends(_svc),
) -> Response:
    await service.delete_subscription(company_id, subscription_id)
    return Response(status_code=204)


# ── Tiers ─────────────────────────────────────────────────────────────────────

@router.get(
    "/tiers",
    response_model=list[TierResponse],
    summary="List available tiers",
)
async def list_tiers(
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> list[TierResponse]:
    return await service.list_tiers()


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.get(
    "/roles",
    response_model=list[RoleResponse],
    summary="List available roles",
)
async def list_roles(
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> list[RoleResponse]:
    return await service.list_roles()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    summary="List all users",
)
async def list_users(
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> list[AdminUserResponse]:
    return await service.list_users()


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=201,
    summary="Create a new user and send welcome email with temp credentials",
)
async def create_user(
    payload: UserCreateRequest,
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> AdminUserResponse:
    return await service.create_user(payload, actor.actor_id)


@router.delete(
    "/users/{user_id}",
    status_code=204,
    summary="Hard delete a user permanently",
)
async def delete_user(
    user_id: uuid.UUID,
    actor:   CurrentActor = Depends(require_roles("admin")),
    service: AdminService = Depends(_svc),
) -> Response:
    await service.hard_delete_user(user_id)
    return Response(status_code=204)
