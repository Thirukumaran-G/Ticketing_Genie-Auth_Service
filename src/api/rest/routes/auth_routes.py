from __future__ import annotations

from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import CurrentActor, get_current_actor
from src.core.services.auth_service import AuthService
from src.core.services.email_service_welcome import EmailService
from src.data.clients.postgres_client import get_db_session
from src.schemas.auth_schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    MessageResponse,
    RegisterResponse,
    ResetPasswordRequest,
    TokenPair,
    UserRegisterRequest,
)

# ── Cookie config ─────────────────────────────────────────────────────────────
COOKIE_SECURE   = True
COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "none"
REFRESH_MAX_AGE = 60 * 60 * 24 * 7


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


router = APIRouter(prefix="", tags=["Authentication"])
_email_service = EmailService()


def _get_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(session)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    summary="Customer self-registration — domain must match a registered company",
)
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


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change own password — all roles",
)
async def change_password(
    payload: ChangePasswordRequest,
    actor:   CurrentActor = Depends(get_current_actor),
    service: AuthService  = Depends(_get_service),
) -> MessageResponse:
    return await service.change_password(actor.actor_id, payload)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset email",
)
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


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    service: AuthService = Depends(_get_service),
) -> MessageResponse:
    return await service.reset_password(payload)
