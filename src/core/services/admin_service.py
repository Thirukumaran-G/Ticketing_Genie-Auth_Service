from __future__ import annotations

import secrets
import string
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.base import ConflictException, NotFoundException
from src.utils.password_utils import hash_password
from src.core.services.email_service import EmailService
from src.data.models.postgres.models import Company, CompanyProductSubscription, Product, User
from src.data.repositories.admin_repository import AdminRepository
from src.data.repositories.user_repository import UserRepository
from src.observability.logging.logger import get_logger
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

logger = get_logger(__name__)

_EMAIL_SVC = EmailService()


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


class AdminService:

    def __init__(self, session: AsyncSession) -> None:
        self._session    = session
        self._admin_repo = AdminRepository(session)
        self._user_repo  = UserRepository(session)

    # ── Company ───────────────────────────────────────────────────────────────

    async def create_company(
        self, payload: CompanyCreateRequest, actor_id: str
    ) -> CompanyResponse:
        if payload.domain:
            existing = await self._admin_repo.get_company_by_domain(payload.domain)
            if existing:
                raise ConflictException(
                    f"Company with domain '{payload.domain}' already exists."
                )
        company = Company(
            name=payload.name,
            domain=payload.domain,
            is_active=True,
            created_by=uuid.UUID(actor_id),
        )
        created = await self._admin_repo.create_company(company)
        await self._session.commit()
        logger.info("company_created", company_id=str(created.id))
        return CompanyResponse.model_validate(created)

    async def delete_company(self, company_id: uuid.UUID) -> None:
        company = await self._admin_repo.get_company_by_id(company_id)
        if not company:
            raise NotFoundException("Company not found.")
        await self._admin_repo.delete_company(company_id)
        await self._session.commit()
        logger.info("company_deleted", company_id=str(company_id))

    async def get_company(self, company_id: uuid.UUID) -> CompanyResponse:
        company = await self._admin_repo.get_company_by_id(company_id)
        if not company:
            raise NotFoundException("Company not found.")
        return CompanyResponse.model_validate(company)

    async def list_companies(self) -> List[CompanyResponse]:
        companies = await self._admin_repo.list_companies()
        return [CompanyResponse.model_validate(c) for c in companies]

    async def update_company(
        self, company_id: uuid.UUID, payload: CompanyUpdateRequest
    ) -> CompanyResponse:
        company = await self._admin_repo.get_company_by_id(company_id)
        if not company:
            raise NotFoundException("Company not found.")
        if payload.domain and payload.domain != company.domain:
            existing = await self._admin_repo.get_company_by_domain(payload.domain)
            if existing:
                raise ConflictException(f"Domain '{payload.domain}' already taken.")
        changes = payload.model_dump(exclude_none=True)
        if changes:
            await self._admin_repo.update_company(company_id, changes)
            await self._session.commit()
        updated = await self._admin_repo.get_company_by_id(company_id)
        return CompanyResponse.model_validate(updated)

    # ── Product ───────────────────────────────────────────────────────────────

    async def create_product(
        self, payload: ProductCreateRequest, actor_id: str
    ) -> ProductResponse:
        existing = await self._admin_repo.get_product_by_code(payload.code)
        if existing:
            raise ConflictException(
                f"Product with code '{payload.code}' already exists."
            )
        product = Product(
            name=payload.name,
            code=payload.code,
            is_active=True,
            created_by=uuid.UUID(actor_id),
        )
        created = await self._admin_repo.create_product(product)
        await self._session.commit()
        logger.info("product_created", product_id=str(created.id))
        return ProductResponse.model_validate(created)

    async def delete_product(self, product_id: uuid.UUID) -> None:
        product = await self._admin_repo.get_product_by_id(product_id)
        if not product:
            raise NotFoundException("Product not found.")
        await self._admin_repo.delete_product(product_id)
        await self._session.commit()
        logger.info("product_deleted", product_id=str(product_id))

    async def list_products(self) -> List[ProductResponse]:
        products = await self._admin_repo.list_products()
        return [ProductResponse.model_validate(p) for p in products]

    async def update_product(
        self, product_id: uuid.UUID, payload: ProductUpdateRequest
    ) -> ProductResponse:
        product = await self._admin_repo.get_product_by_id(product_id)
        if not product:
            raise NotFoundException("Product not found.")
        changes = payload.model_dump(exclude_none=True)
        if changes:
            await self._admin_repo.update_product(product_id, changes)
            await self._session.commit()
        updated = await self._admin_repo.get_product_by_id(product_id)
        return ProductResponse.model_validate(updated)

    # ── Subscription ──────────────────────────────────────────────────────────

    async def assign_subscription(
        self,
        company_id: uuid.UUID,
        payload: SubscriptionAssignRequest,
        actor_id: str,
    ) -> SubscriptionResponse:
        company = await self._admin_repo.get_company_by_id(company_id)
        if not company:
            raise NotFoundException("Company not found.")
        product = await self._admin_repo.get_product_by_id(payload.product_id)
        if not product:
            raise NotFoundException("Product not found.")
        tier = await self._admin_repo.get_tier_by_id(payload.tier_id)
        if not tier:
            raise NotFoundException("Tier not found.")
        existing = await self._admin_repo.get_active_subscription(
            company_id, payload.product_id
        )
        if existing:
            raise ConflictException(
                "An active subscription already exists for this company/product. "
                "Deactivate it first."
            )
        sub = CompanyProductSubscription(
            company_id=company_id,
            product_id=payload.product_id,
            tier_id=payload.tier_id,
            assigned_by=uuid.UUID(actor_id),
            is_active=True,
        )
        created = await self._admin_repo.create_subscription(sub)
        await self._session.commit()
        logger.info(
            "subscription_assigned",
            company_id=str(company_id),
            product_id=str(payload.product_id),
        )
        return await self._build_sub_response(created)

    async def delete_subscription(
        self, company_id: uuid.UUID, subscription_id: uuid.UUID
    ) -> None:
        sub = await self._admin_repo.get_subscription_by_id(subscription_id)
        if not sub or sub.company_id != company_id:
            raise NotFoundException("Subscription not found.")
        await self._admin_repo.delete_subscription(subscription_id)
        await self._session.commit()
        logger.info("subscription_deleted", subscription_id=str(subscription_id))

    async def update_subscription(
        self,
        company_id: uuid.UUID,
        subscription_id: uuid.UUID,
        payload: SubscriptionUpdateRequest,
        actor_id: str,
    ) -> SubscriptionResponse:
        sub = await self._admin_repo.get_subscription_by_id(subscription_id)
        if not sub or sub.company_id != company_id:
            raise NotFoundException("Subscription not found.")
        if payload.tier_id:
            tier = await self._admin_repo.get_tier_by_id(payload.tier_id)
            if not tier:
                raise NotFoundException("Tier not found.")
        changes = payload.model_dump(exclude_none=True)
        if changes:
            await self._admin_repo.update_subscription(subscription_id, changes)
            await self._session.commit()
        updated = await self._admin_repo.get_subscription_by_id(subscription_id)
        return await self._build_sub_response(updated)

    async def list_subscriptions(
        self, company_id: uuid.UUID
    ) -> List[SubscriptionResponse]:
        subs = await self._admin_repo.list_subscriptions(company_id)
        return [await self._build_sub_response(s) for s in subs]

    async def _build_sub_response(
        self, sub: CompanyProductSubscription
    ) -> SubscriptionResponse:
        product = await self._admin_repo.get_product_by_id(sub.product_id)
        tier    = await self._admin_repo.get_tier_by_id(sub.tier_id)
        return SubscriptionResponse(
            id=sub.id,
            company_id=sub.company_id,
            product_id=sub.product_id,
            product_name=product.name,
            product_code=product.code,
            tier_id=sub.tier_id,
            tier_name=tier.name,
            is_active=sub.is_active,
            assigned_at=sub.assigned_at,
        )

    # ── Tiers ─────────────────────────────────────────────────────────────────

    async def list_tiers(self) -> List[TierResponse]:
        tiers = await self._admin_repo.list_tiers()
        return [TierResponse.model_validate(t) for t in tiers]

    # ── Roles ─────────────────────────────────────────────────────────────────

    async def list_roles(self) -> List[RoleResponse]:
        roles = await self._admin_repo.list_roles()
        return [RoleResponse.model_validate(r) for r in roles]

    # ── Users ─────────────────────────────────────────────────────────────────

    async def list_users(self) -> List[AdminUserResponse]:
        users = await self._admin_repo.list_users()
        result = []
        for user in users:
            role_name = await self._user_repo.get_role_name_by_id(user.role_id)
            result.append(AdminUserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=role_name or "unknown",
                company_id=user.company_id,
                is_active=user.is_active,
                last_login=user.last_login,
                created_at=user.created_at,
            ))
        return result

    async def create_user(
        self, payload: UserCreateRequest, actor_id: str
    ) -> AdminUserResponse:
        existing = await self._user_repo.get_by_email(payload.email)
        if existing:
            raise ConflictException(f"User with email '{payload.email}' already exists.")

        role = await self._user_repo.get_role_by_name(payload.role)
        if not role:
            raise NotFoundException(f"Role '{payload.role}' not found.")

        temp_password = _generate_temp_password()
        hashed        = hash_password(temp_password)

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hashed,
            role_id=role.id,
            preferred_contact=payload.preferred_contact or "email",
            is_active=True,
        )
        created = await self._user_repo.create(user)
        await self._session.commit()
        logger.info("user_created_by_admin", user_id=str(created.id), role=payload.role)

        try:
            await _EMAIL_SVC.send_welcome_credentials(
                to_email=created.email,
                full_name=created.full_name,
                role=payload.role,
                temp_password=temp_password,
            )
        except Exception as exc:
            logger.error("welcome_email_failed", user_id=str(created.id), error=str(exc))

        return AdminUserResponse(
            id=created.id,
            email=created.email,
            full_name=created.full_name,
            role=payload.role,
            company_id=created.company_id,
            is_active=created.is_active,
            last_login=created.last_login,
            created_at=created.created_at,
        )

    async def hard_delete_user(self, user_id: uuid.UUID) -> None:
        """Permanently remove a user row from the database."""
        from sqlalchemy import delete
        from src.data.models.postgres.models import User

        user = await self._session.get(User, user_id)
        if not user:
            raise NotFoundException("User not found.")

        await self._session.execute(
            delete(User).where(User.id == user_id)
        )
        await self._session.commit()
        logger.info("user_hard_deleted", user_id=str(user_id))