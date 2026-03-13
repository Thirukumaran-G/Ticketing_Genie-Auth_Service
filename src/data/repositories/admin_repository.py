from __future__ import annotations

import uuid
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.models import (
    Company, Product, Role, Tier, CompanyProductSubscription, User
)


class AdminRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Company ───────────────────────────────────────────────────────────────

    async def create_company(self, company: Company) -> Company:
        self._session.add(company)
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def get_company_by_id(self, company_id: uuid.UUID) -> Optional[Company]:
        result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_company_by_domain(self, domain: str) -> Optional[Company]:
        result = await self._session.execute(
            select(Company).where(Company.domain == domain)
        )
        return result.scalar_one_or_none()

    async def list_companies(self) -> List[Company]:
        result = await self._session.execute(
            select(Company).order_by(Company.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_company(self, company_id: uuid.UUID) -> None:
        from sqlalchemy import delete
        await self._session.execute(
            delete(Company).where(Company.id == company_id)
        )
        await self._session.flush()

    async def update_company(self, company_id: uuid.UUID, changes: dict) -> None:
        await self._session.execute(
            update(Company).where(Company.id == company_id).values(**changes)
        )
        await self._session.flush()

    # ── Product ───────────────────────────────────────────────────────────────

    async def create_product(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def delete_product(self, product_id: uuid.UUID) -> None:
        from sqlalchemy import delete
        await self._session.execute(
            delete(Product).where(Product.id == product_id)
        )
        await self._session.flush()

    async def get_product_by_id(self, product_id: uuid.UUID) -> Optional[Product]:
        result = await self._session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_product_by_code(self, code: str) -> Optional[Product]:
        result = await self._session.execute(
            select(Product).where(Product.code == code)
        )
        return result.scalar_one_or_none()

    async def list_products(self) -> List[Product]:
        result = await self._session.execute(
            select(Product).order_by(Product.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_product(self, product_id: uuid.UUID, changes: dict) -> None:
        await self._session.execute(
            update(Product).where(Product.id == product_id).values(**changes)
        )
        await self._session.flush()

    # ── Tier ──────────────────────────────────────────────────────────────────

    async def list_tiers(self) -> List[Tier]:
        result = await self._session.execute(
            select(Tier).where(Tier.is_active == True).order_by(Tier.name)
        )
        return list(result.scalars().all())

    async def get_tier_by_id(self, tier_id: uuid.UUID) -> Optional[Tier]:
        result = await self._session.execute(
            select(Tier).where(Tier.id == tier_id)
        )
        return result.scalar_one_or_none()

    # ── Roles ─────────────────────────────────────────────────────────────────

    async def list_roles(self) -> List[Role]:
        """Return all active roles — used to populate the create-user dropdown."""
        result = await self._session.execute(
            select(Role).where(Role.is_active == True).order_by(Role.name)
        )
        return list(result.scalars().all())

    # ── Subscription ──────────────────────────────────────────────────────────

    async def create_subscription(
        self, sub: CompanyProductSubscription
    ) -> CompanyProductSubscription:
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

    async def get_subscription_by_id(
        self, subscription_id: uuid.UUID
    ) -> Optional[CompanyProductSubscription]:
        result = await self._session.execute(
            select(CompanyProductSubscription).where(
                CompanyProductSubscription.id == subscription_id
            )
        )
        return result.scalar_one_or_none()

    async def get_active_subscription(
        self, company_id: uuid.UUID, product_id: uuid.UUID
    ) -> Optional[CompanyProductSubscription]:
        result = await self._session.execute(
            select(CompanyProductSubscription).where(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.product_id == product_id,
                CompanyProductSubscription.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_subscriptions(
        self, company_id: uuid.UUID
    ) -> List[CompanyProductSubscription]:
        result = await self._session.execute(
            select(CompanyProductSubscription)
            .where(CompanyProductSubscription.company_id == company_id)
            .order_by(CompanyProductSubscription.assigned_at.desc())
        )
        return list(result.scalars().all())

    async def update_subscription(
        self, subscription_id: uuid.UUID, changes: dict
    ) -> None:
        await self._session.execute(
            update(CompanyProductSubscription)
            .where(CompanyProductSubscription.id == subscription_id)
            .values(**changes)
        )
        await self._session.flush()

    async def delete_subscription(self, subscription_id: uuid.UUID) -> None:
        from sqlalchemy import delete
        await self._session.execute(
            delete(CompanyProductSubscription).where(
                CompanyProductSubscription.id == subscription_id
            )
        )
        await self._session.flush()

    # ── Users ─────────────────────────────────────────────────────────────────

    async def list_users(self) -> List[User]:
        result = await self._session.execute(
            select(User).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())