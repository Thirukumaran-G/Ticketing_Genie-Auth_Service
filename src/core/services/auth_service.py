from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.core.exceptions.base import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
    TokenRevokedException,
    ValidationException,
)
from src.data.models.postgres.models import PasswordResetToken, RevokeToken, User
from src.data.repositories.password_reset_repository import PasswordResetRepository
from src.data.repositories.revoke_token_repository import RevokeTokenRepository
from src.data.repositories.user_repository import UserRepository
from src.observability.logging.logger import get_logger
from src.schemas.auth_schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InternalUserCreateRequest,
    InternalUserCreateResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    RegisterResponse,
    ResetPasswordRequest,
    TokenPair,
    UserRegisterRequest,
)
from src.utils.jwt_utils import create_access_token, create_refresh_token, decode_token
from src.utils.password_utils import (
    generate_secure_password,
    hash_password,
    verify_password,
)

logger = get_logger(__name__)

_RESET_EXPIRE_MINUTES = 30


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _extract_domain(email: str) -> str:
    return email.split("@", 1)[1].lower()


class AuthService:

    def __init__(self, session: AsyncSession) -> None:
        self._session     = session
        self._user_repo   = UserRepository(session)
        self._token_repo  = RevokeTokenRepository(session)
        self._reset_repo  = PasswordResetRepository(session)

    # customer registration domain based
    async def register_user(self, payload: UserRegisterRequest) -> RegisterResponse:
        existing = await self._user_repo.get_by_email(payload.email)
        if existing:
            raise ConflictException(f"An account with email {payload.email} already exists.")
        domain  = _extract_domain(payload.email)
        company = await self._user_repo.get_company_by_domain(domain)
        if not company:
            raise ValidationException(
                "Your organization is not registered."
            )
        role = await self._user_repo.get_role_by_name("customer")
        if not role:
            raise ValidationException("Role 'customer' not found.")

        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role_id=role.id,
            company_id=company.id,
            ph_no=getattr(payload, "ph_no", None),
            is_active=True,
        )
        created = await self._user_repo.create(user)
        await self._session.commit()

        logger.info("customer_registered", user_id=str(created.id), company_id=str(company.id))
        return RegisterResponse(
            id=created.id,
            email=created.email,
            full_name=created.full_name,
            role="customer",
            company_id=company.id,
            created_at=created.created_at,
        )

    # ── Internal staff creation ───────────────────────────────────────────────

    async def internal_create_user(
        self, payload: InternalUserCreateRequest
    ) -> InternalUserCreateResponse:
        existing = await self._user_repo.get_by_email(payload.email)
        if existing:
            raise ConflictException(f"User with email {payload.email} already exists.")

        role = await self._user_repo.get_role_by_name(payload.role)
        if not role:
            raise ValidationException(f"Role '{payload.role}' not found. Run role seeder.")

        temp_password = generate_secure_password(length=16)
        user = User(
            email=payload.email,
            hashed_password=hash_password(temp_password),
            full_name=payload.full_name,
            role_id=role.id,
            is_active=True,
        )
        created = await self._user_repo.create(user)
        await self._session.commit()

        logger.info("internal_user_created", user_id=str(created.id), role=payload.role)
        return InternalUserCreateResponse(
            user_id=created.id,
            email=created.email,
            full_name=created.full_name,
            role=payload.role,
            temp_password=temp_password,
        )

    # login
    async def login(self, payload: LoginRequest) -> TokenPair:
        user = await self._user_repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise AuthenticationException("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationException("Account is deactivated. Please contact support.")
        if user.deleted_at is not None:
            raise AuthenticationException("Account not found.")

        role_name = await self._user_repo.get_role_name_by_id(user.role_id)
        if not role_name:
            raise AuthenticationException("No role assigned to this account.")

        await self._user_repo.update_fields(
            user.id, {"last_login": datetime.now(UTC)}
        )

        product_tiers: dict[str, Any] | None = None
        company_id:    str | None  = None

        if role_name == "customer":
            if not user.company_id:
                raise AuthenticationException(
                    "No company assigned to this account. Contact support."
                )
            company_id    = str(user.company_id)
            product_tiers = await self._user_repo.get_product_tiers_for_company(user.company_id)

        token_pair = await self._issue_tokens(
            user_id=user.id,
            role_name=role_name,
            email=user.email,
            company_id=company_id,
            product_tiers=product_tiers,
        )
        logger.info("login", user_id=str(user.id), role=role_name)
        return token_pair

    # token generation
    async def _issue_tokens(
        self,
        user_id:       uuid.UUID,
        role_name:     str,
        email:         str | None  = None,
        company_id:    str | None  = None,
        product_tiers: dict[str, Any] | None = None,
        family_id:     str | None  = None,
    ) -> TokenPair:
        fid        = family_id or str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        access_token, _exp = create_access_token(
            actor_id=str(user_id),
            role_name=role_name,
            email=email,
            company_id=company_id,
            product_tiers=product_tiers,
        )
        refresh_token_str, jti, sid, rt_expire = create_refresh_token(
            actor_id=str(user_id),
            role_name=role_name,
            family_id=fid,
            session_id=session_id,
        )
        revoke_record = RevokeToken(
            user_id=user_id,
            jti=jti,
            family_id=fid,
            session_id=sid,
            is_revoked=False,
            expires_at=rt_expire,
        )
        await self._token_repo.create(revoke_record)
        await self._session.commit()

        logger.info("tokens_issued", user_id=str(user_id), role=role_name)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token_str,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # refresh tokens
    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise AuthenticationException("Invalid token type.")

        jti         = payload["jti"]
        family_id   = payload["family_id"]
        user_id_str = payload["sub"]

        token_record = await self._token_repo.get_by_jti(jti)
        if not token_record:
            raise TokenRevokedException("Refresh token not found.")

        if token_record.is_revoked:
            await self._token_repo.revoke_family(family_id)
            await self._session.commit()
            logger.warning("token_theft_detected", family_id=family_id, user_id=user_id_str)
            raise TokenRevokedException(
                "Security alert: token reuse detected. Please log in again."
            )

        await self._token_repo.revoke_by_jti(jti)

        user = await self._user_repo.get_active_by_id(user_id_str)
        if not user:
            raise AuthenticationException("User not found or deactivated.")

        resolved_role = await self._user_repo.get_role_name_by_id(user.role_id)
        if not resolved_role:
            raise AuthenticationException("No role assigned. Contact support.")

        product_tiers: dict[str, Any] | None = None
        company_id:    str | None  = None

        if resolved_role == "customer":
            if not user.company_id:
                raise AuthenticationException("No company assigned. Contact support.")
            company_id    = str(user.company_id)
            product_tiers = await self._user_repo.get_product_tiers_for_company(user.company_id)

        return await self._issue_tokens(
            user_id=user.id,
            role_name=resolved_role,
            email=user.email,
            company_id=company_id,
            product_tiers=product_tiers,
            family_id=family_id,
        )

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, refresh_token: str) -> None:
        try:
            payload   = decode_token(refresh_token)
            jti       = payload["jti"]
            family_id = payload["family_id"]
            record    = await self._token_repo.get_by_jti(jti)
            if record:
                await self._token_repo.revoke_family(family_id)
                await self._session.commit()
            logger.info("logout", jti=jti)
        except Exception:
            logger.warning("logout_with_invalid_token")

    # ── Me ────────────────────────────────────────────────────────────────────

    async def get_me(self, user_id_str: str) -> MeResponse:
        user = await self._user_repo.get_active_by_id(user_id_str)
        if not user:
            raise NotFoundException("User not found.")

        role_name = await self._user_repo.get_role_name_by_id(user.role_id)
        if not role_name:
            raise NotFoundException("No role assigned to this account.")

        product_tiers: dict[str, Any] | None = None
        if role_name == "customer" and user.company_id:
            product_tiers = await self._user_repo.get_product_tiers_for_company(user.company_id)

        return MeResponse(
            actor_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role_name,
            preferred_contact=user.preferred_contact,
            company_id=user.company_id,
            product_tiers=product_tiers,
            is_active=user.is_active,
        )

    # ── Change password ───────────────────────────────────────────────────────

    async def change_password(
        self, user_id_str: str, payload: ChangePasswordRequest
    ) -> MessageResponse:
        user = await self._user_repo.get_active_by_id(user_id_str)
        if not user:
            raise NotFoundException("User not found.")
        if not verify_password(payload.current_password, user.hashed_password):
            raise AuthenticationException("Current password is incorrect.")
        await self._user_repo.update_fields(
            user.id, {"hashed_password": hash_password(payload.new_password)}
        )
        await self._session.commit()
        logger.info("password_changed", user_id=str(user.id))
        return MessageResponse(message="Password updated successfully.")

    # ── Forgot password ───────────────────────────────────────────────────────

    async def forgot_password(
        self, payload: ForgotPasswordRequest
    ) -> tuple[str, User] | None:
        user = await self._user_repo.get_by_email(payload.email)
        if not user or not user.is_active or user.deleted_at is not None:
            return None
        await self._reset_repo.invalidate_existing(user.id)
        await self._session.flush()

        # Step 2: generate a fresh token and insert it
        raw_token = secrets.token_urlsafe(48)
        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=_RESET_EXPIRE_MINUTES),
        )
        await self._reset_repo.create(reset)
        await self._session.commit()

        logger.info("password_reset_requested", user_id=str(user.id))
        return raw_token, user

    # ── Reset password ────────────────────────────────────────────────────────

    async def reset_password(self, payload: ResetPasswordRequest) -> MessageResponse:
        reset_record = await self._reset_repo.get_valid_token(_hash_token(payload.token))
        if not reset_record:
            raise ValidationException(
                "Reset link is invalid or has expired. Please request a new one."
            )

        user = await self._user_repo.get_active_by_id(reset_record.user_id)
        if not user:
            raise NotFoundException("Account not found.")

        await self._user_repo.update_fields(
            user.id, {"hashed_password": hash_password(payload.new_password)}
        )
        await self._reset_repo.mark_used(reset_record.id)
        await self._token_repo.revoke_all_for_user(user.id)
        await self._session.commit()

        logger.info("password_reset", user_id=str(user.id))
        return MessageResponse(
            message="Password reset successfully. Please log in with your new password."
        )

    # ── Get user email (internal) ─────────────────────────────────────────────

    async def get_user_email(self, user_id: str) -> dict[str, Any]:
        user = await self._user_repo.get_active_by_id(user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found.")
        return {"user_id": user.id, "email": user.email}
