from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.models import (
    Company,
    CompanyProductSubscription,
    Product,
    Role,
    Tier,
    User,
)


class InternalRepository:
    """
    DB access layer for all /internal/* endpoints.

    Owns queries against: Tier, Company, Product, CompanyProductSubscription,
    and the user/role lookups that are unique to internal operations
    (preferred-contact update, create-or-get customer, role-by-name).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── User (internal-specific operations) ───────────────────────────────────

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Bare fetch by PK — used by GET /internal/users/{id}."""
        return await self._session.get(User, user_id)

    async def get_active_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a non-deleted, active user — used by customer-tier lookup."""
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Used by create-or-get customer to detect duplicates."""
        result = await self._session.execute(
            select(User).where(
                func.lower(User.email) == email.lower().strip(),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_user_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(
                func.lower(User.email) == email.lower().strip(),
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def save_user(self, user: User) -> User:
        """Persist a new user and return the refreshed instance."""
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        await self._session.commit()
        return user

    async def update_user_preferred_contact(
        self, user_id: uuid.UUID, preferred_contact: str
    ) -> User | None:
        """Patch preferred_contact in-place; returns None when user not found."""
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.preferred_contact = preferred_contact
        await self._session.commit()
        return user

    # ── Role ──────────────────────────────────────────────────────────────────

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        """Used by GET /internal/users/{id} to resolve role name."""
        return await self._session.get(Role, role_id)

    async def get_role_by_name(self, name: str) -> Role | None:
        """Used by create-or-get customer to assign the 'customer' role."""
        result = await self._session.execute(
            select(Role).where(
                func.lower(Role.name) == name.lower(),
                Role.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    # ── Tier ──────────────────────────────────────────────────────────────────

    async def get_tier_by_name(self, tier_name: str) -> Tier | None:
        """Used by GET /internal/tiers/by-name/{tier_name}."""
        result = await self._session.execute(
            select(Tier).where(
                Tier.name == tier_name,
                Tier.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_customer_tier(
    self,
    company_id: uuid.UUID,
    product_id: uuid.UUID | None = None,
) -> tuple[CompanyProductSubscription, Tier] | None:
        """
        Returns the active (subscription, tier) pair for a company.
        Optionally filtered to a specific product.
        Used by GET /internal/customers/{id}/tier.
        """
        stmt = (
            select(CompanyProductSubscription, Tier)
            .join(Tier, Tier.id == CompanyProductSubscription.tier_id)
            .where(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.is_active.is_(True),
            )
        )
        if product_id:
            stmt = stmt.where(CompanyProductSubscription.product_id == product_id)

        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        sub, tier = row
        return sub, tier

    # ── Company ───────────────────────────────────────────────────────────────

    async def get_company_by_domain(self, domain: str) -> Company | None:
        """Used by GET /internal/companies/by-domain/{domain}."""
        result = await self._session.execute(
            select(Company).where(
                func.lower(Company.domain) == domain.lower().strip(),
                Company.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    # ── Product ───────────────────────────────────────────────────────────────

    async def list_active_products(self) -> list[Product]:
        """Used by GET /internal/products/active."""
        rows = (
            await self._session.execute(
                select(Product)
                .where(Product.is_active.is_(True))
                .order_by(Product.name)
            )
        ).scalars().all()
        return list(rows)
