# Auth service
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import CurrentActor, get_current_actor
from src.core.services.auth_service import AuthService
from src.core.services.email_service import EmailService
from src.data.clients.postgres_client import get_db_session
from src.schemas.auth_schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InternalUserCreateRequest,
    InternalUserCreateResponse,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    MessageResponse,
    RefreshTokenRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenPair,
    TokenValidationResponse,
    UserEmailResponse,
    UserRegisterRequest,
)
from pydantic import BaseModel as _BaseModel
from fastapi import HTTPException
from src.data.models.postgres.models import Role,User


class TierLookupResponse(_BaseModel):
    tier_id:   str
    tier_name: str

router = APIRouter(prefix="", tags=["Authentication"])
_email_service = EmailService()


def _get_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(session)


@router.post("/register", response_model=RegisterResponse, status_code=201,
             summary="Customer self-registration — domain must match a registered company")
async def register_user(
    payload: UserRegisterRequest,
    service: AuthService = Depends(_get_service),
) -> RegisterResponse:
    return await service.register_user(payload)


@router.post("/login", response_model=TokenPair, summary="Login — all roles")
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(_get_service),
) -> TokenPair:
    return await service.login(payload)


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
async def refresh_token(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(_get_service),
) -> TokenPair:
    return await service.refresh_tokens(payload.refresh_token)


@router.post("/logout", status_code=204, summary="Logout — revoke token family")
async def logout(
    payload: LogoutRequest,
    service: AuthService = Depends(_get_service),
) -> Response:
    await service.logout(payload.refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse, summary="Current user profile — all roles")
async def get_me(
    actor:   CurrentActor = Depends(get_current_actor),
    service: AuthService  = Depends(_get_service),
) -> MeResponse:
    return await service.get_me(actor.actor_id)


@router.post("/change-password", response_model=MessageResponse,
             summary="Change own password — all roles")
async def change_password(
    payload: ChangePasswordRequest,
    actor:   CurrentActor = Depends(get_current_actor),
    service: AuthService  = Depends(_get_service),
) -> MessageResponse:
    return await service.change_password(actor.actor_id, payload)


@router.post("/forgot-password", response_model=MessageResponse,
             summary="Request password reset email")
async def forgot_password(
    payload:          ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    service:          AuthService = Depends(_get_service),
) -> MessageResponse:
    result = await service.forgot_password(payload)
    if result:
        raw_token, user = result
        background_tasks.add_task(
            _email_service.send_password_reset,
            to_email=user.email,
            full_name=user.full_name,
            reset_token=raw_token,
        )
    return MessageResponse(
        message="If an account exists with this email, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse,
             summary="Reset password with token")
async def reset_password(
    payload: ResetPasswordRequest,
    service: AuthService = Depends(_get_service),
) -> MessageResponse:
    return await service.reset_password(payload)


# ── Internal (hidden from docs) ───────────────────────────────────────────────

@router.post("/internal/users", response_model=InternalUserCreateResponse,
             status_code=201, include_in_schema=False)
async def internal_create_user(
    payload: InternalUserCreateRequest,
    service: AuthService = Depends(_get_service),
) -> InternalUserCreateResponse:
    return await service.internal_create_user(payload)

@router.get("/internal/users/{user_id}")
async def get_user_internal(user_id: str, session: AsyncSession = Depends(get_db_session)):
    user = await session.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(404)
    role = await session.get(Role, user.role_id)
    return {
                "id":        str(user.id),
                "email":     user.email,
                "full_name": user.full_name,
                "role":      role.name if role else None,
                "is_active": user.is_active,
            }


@router.post("/internal/validate", response_model=TokenValidationResponse,
             include_in_schema=False)
async def internal_validate_token(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(_get_service),
) -> TokenValidationResponse:
    return await service.validate_token(payload.refresh_token)


@router.get("/internal/users/{user_id}/email", response_model=UserEmailResponse,
            include_in_schema=False)
async def internal_get_user_email(
    user_id: uuid.UUID,
    service: AuthService = Depends(_get_service),
) -> UserEmailResponse:
    return await service.get_user_email(str(user_id))


@router.get(
    "/internal/tiers/by-name/{tier_name}",
    response_model=TierLookupResponse,
    include_in_schema=False,
    summary="Resolve tier UUID from name — used by ticket-service workers",
)
async def internal_get_tier_by_name(
    tier_name: str,
    session:   AsyncSession = Depends(get_db_session),
) -> TierLookupResponse:
    from sqlalchemy import select
    from src.data.models.postgres.models import Tier

    result = await session.execute(
        select(Tier).where(
            Tier.name == tier_name,
            Tier.is_active.is_(True),
        )
    )
    tier = result.scalar_one_or_none()
    if not tier:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Tier '{tier_name}' not found")

    return TierLookupResponse(tier_id=str(tier.id), tier_name=tier.name)


@router.get(
    "/internal/customers/{user_id}/tier",
    response_model=TierLookupResponse,
    include_in_schema=False,
    summary="Get active tier for a customer — used by ticket-service SLA worker",
)
async def internal_get_customer_tier(
    user_id:    uuid.UUID,
    product_id: uuid.UUID | None = None,
    session:    AsyncSession = Depends(get_db_session),
) -> TierLookupResponse:
    from sqlalchemy import select
    from fastapi import HTTPException
    from src.data.models.postgres.models import (
        User, CompanyProductSubscription, Tier
    )

    # 1. Load user
    user = (
        await session.execute(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not user.company_id:
        raise HTTPException(status_code=404, detail="Customer has no associated company")

    stmt = (
        select(CompanyProductSubscription, Tier)
        .join(Tier, Tier.id == CompanyProductSubscription.tier_id)
        .where(
            CompanyProductSubscription.company_id == user.company_id,
            CompanyProductSubscription.is_active.is_(True),
        )
    )
    if product_id:
        stmt = stmt.where(CompanyProductSubscription.product_id == product_id)

    row = (await session.execute(stmt)).first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="No active product subscription found for this customer",
        )

    _, tier = row
    return TierLookupResponse(tier_id=str(tier.id), tier_name=tier.name)