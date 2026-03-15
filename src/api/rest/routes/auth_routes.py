"""Auth service routes — sets httpOnly cookies on login/refresh/logout."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
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
    ProductListResponse,
    CompanyByDomainResponse,
    InternalCustomerCreateResponse,
    InternalCustomerCreateRequest
)
from pydantic import BaseModel as _BaseModel
from src.data.models.postgres.models import Role, User

# ── Cookie config ─────────────────────────────────────────────────────────────
COOKIE_SECURE   = False   # flip to True in production (HTTPS)
COOKIE_SAMESITE = "lax"
REFRESH_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_MAX_AGE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/")


class TierLookupResponse(_BaseModel):
    tier_id:   str
    tier_name: str


router = APIRouter(prefix="", tags=["Authentication"])
_email_service = EmailService()


def _get_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(session)


# ── Public routes ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=201,
             summary="Customer self-registration — domain must match a registered company")
async def register_user(
    payload: UserRegisterRequest,
    service: AuthService = Depends(_get_service),
) -> RegisterResponse:
    return await service.register_user(payload)


@router.post("/login", response_model=TokenPair, summary="Login — all roles")
async def login(
    payload:  LoginRequest,
    response: Response,
    service:  AuthService = Depends(_get_service),
) -> TokenPair:
    tokens = await service.login(payload)
    # Only refresh token in cookie — access token goes to frontend memory via response body
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
async def refresh_token(
    request:  Request,
    response: Response,
    service:  AuthService = Depends(_get_service),
) -> TokenPair:
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="No refresh token provided.")
    tokens = await service.refresh_tokens(rt)
    # Rotate refresh cookie, return new access token in body
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=204, summary="Logout — revoke token family")
async def logout(
    request:  Request,
    response: Response,
    payload:  LogoutRequest,
    service:  AuthService = Depends(_get_service),
) -> Response:
    rt = (payload.refresh_token if payload.refresh_token else None) \
        or request.cookies.get("refresh_token")
    if rt:
        await service.logout(rt)
    _clear_auth_cookies(response)
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


@router.get("/internal/users/{user_id}", include_in_schema=False)
async def get_user_internal(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
):
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
)
async def internal_get_tier_by_name(
    tier_name: str,
    session:   AsyncSession = Depends(get_db_session),
) -> TierLookupResponse:
    from sqlalchemy import select
    from src.data.models.postgres.models import Tier

    result = await session.execute(
        select(Tier).where(Tier.name == tier_name, Tier.is_active.is_(True))
    )
    tier = result.scalar_one_or_none()
    if not tier:
        raise HTTPException(status_code=404, detail=f"Tier '{tier_name}' not found")
    return TierLookupResponse(tier_id=str(tier.id), tier_name=tier.name)


@router.get(
    "/internal/customers/{user_id}/tier",
    response_model=TierLookupResponse,
    include_in_schema=False,
)
async def internal_get_customer_tier(
    user_id:    uuid.UUID,
    product_id: uuid.UUID | None = None,
    session:    AsyncSession = Depends(get_db_session),
) -> TierLookupResponse:
    from sqlalchemy import select
    from src.data.models.postgres.models import CompanyProductSubscription, Tier

    user = (
        await session.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
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


@router.get(
    "/internal/products/active",
    response_model=ProductListResponse,
    include_in_schema=False,
)
async def internal_list_active_products(
    session: AsyncSession = Depends(get_db_session),
) -> ProductListResponse:
    from sqlalchemy import select
    from src.data.models.postgres.models import Product

    rows = (
        await session.execute(
            select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
        )
    ).scalars().all()

    return ProductListResponse(
        products=[
            {
                "id":          str(p.id),
                "name":        p.name,
                "code":        p.code,
                "description": p.description,
            }
            for p in rows
        ]
    )


@router.get(
    "/internal/companies/by-domain/{domain}",
    response_model=CompanyByDomainResponse,
    include_in_schema=False,
)
async def internal_get_company_by_domain(
    domain:  str,
    session: AsyncSession = Depends(get_db_session),
) -> CompanyByDomainResponse:
    from sqlalchemy import select, func
    from src.data.models.postgres.models import Company

    result = await session.execute(
        select(Company).where(
            func.lower(Company.domain) == domain.lower().strip(),
            Company.is_active.is_(True),
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"No active company for domain '{domain}'")

    return CompanyByDomainResponse(
        company_id=str(company.id),
        company_name=company.name,
        domain=company.domain or domain,
    )


@router.post(
    "/internal/customers/create-or-get",
    response_model=InternalCustomerCreateResponse,
    include_in_schema=False,
)
async def internal_create_or_get_customer(
    payload: InternalCustomerCreateRequest,
    service: AuthService = Depends(_get_service),
    session: AsyncSession = Depends(get_db_session),
) -> InternalCustomerCreateResponse:
    from sqlalchemy import select, func
    from src.data.models.postgres.models import User, Role
    from src.utils.password_utils import hash_password, generate_secure_password
    import uuid6

    existing_result = await session.execute(
        select(User).where(
            func.lower(User.email) == payload.email.lower().strip(),
            User.deleted_at.is_(None),
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        return InternalCustomerCreateResponse(
            user_id=str(existing.id),
            email=existing.email,
            full_name=existing.full_name or "",
            temp_password="",
            is_new=False,
        )

    role_result = await session.execute(
        select(Role).where(
            func.lower(Role.name) == "customer",
            Role.is_active.is_(True),
        )
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=500, detail="Customer role not found — run seeder.")

    temp_password = generate_secure_password(length=16)

    new_user = User(
        id=uuid6.uuid7(),
        email=payload.email.lower().strip(),
        hashed_password=hash_password(temp_password),
        full_name=payload.full_name,
        company_id=uuid.UUID(payload.company_id),
        role_id=role.id,
        preferred_contact=payload.preferred_contact,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()
    await session.refresh(new_user)
    await session.commit()

    return InternalCustomerCreateResponse(
        user_id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name or "",
        temp_password=temp_password,
        is_new=True,
    )