from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.models import (
    Company,
    CompanyProductSubscription,
    Product,
    Tier,
    User,
)


class AdminRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── Company ───────────────────────────────────────────────────────────────

    async def create_company(self, company: Company) -> Company:
        self._s.add(company)
        await self._s.flush()
        return company

    async def get_company_by_id(self, company_id: uuid.UUID) -> Optional[Company]:
        result = await self._s.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_company_by_domain(self, domain: str) -> Optional[Company]:
        result = await self._s.execute(
            select(Company).where(Company.domain == domain)
        )
        return result.scalar_one_or_none()

    async def update_company(
        self, company_id: uuid.UUID, fields: Dict[str, Any]
    ) -> None:
        await self._s.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**fields)
        )

    async def list_companies(self) -> List[Company]:
        result = await self._s.execute(
            select(Company).order_by(Company.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Product ───────────────────────────────────────────────────────────────

    async def create_product(self, product: Product) -> Product:
        self._s.add(product)
        await self._s.flush()
        return product

    async def get_product_by_id(self, product_id: uuid.UUID) -> Optional[Product]:
        result = await self._s.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_product_by_code(self, code: str) -> Optional[Product]:
        result = await self._s.execute(
            select(Product).where(Product.code == code)
        )
        return result.scalar_one_or_none()

    async def update_product(
        self, product_id: uuid.UUID, fields: Dict[str, Any]
    ) -> None:
        await self._s.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(**fields)
        )

    async def list_products(self) -> List[Product]:
        result = await self._s.execute(
            select(Product).order_by(Product.created_at.desc())
        )
        return list(result.scalars().all())

    # ── CompanyProductSubscription ────────────────────────────────────────────

    async def create_subscription(
        self, sub: CompanyProductSubscription
    ) -> CompanyProductSubscription:
        self._s.add(sub)
        await self._s.flush()
        return sub

    async def get_subscription_by_id(
        self, sub_id: uuid.UUID
    ) -> Optional[CompanyProductSubscription]:
        result = await self._s.execute(
            select(CompanyProductSubscription).where(
                CompanyProductSubscription.id == sub_id
            )
        )
        return result.scalar_one_or_none()

    async def get_active_subscription(
        self, company_id: uuid.UUID, product_id: uuid.UUID
    ) -> Optional[CompanyProductSubscription]:
        result = await self._s.execute(
            select(CompanyProductSubscription).where(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.product_id == product_id,
                CompanyProductSubscription.is_active  == True,
            )
        )
        return result.scalar_one_or_none()

    async def update_subscription(
        self, sub_id: uuid.UUID, fields: Dict[str, Any]
    ) -> None:
        await self._s.execute(
            update(CompanyProductSubscription)
            .where(CompanyProductSubscription.id == sub_id)
            .values(**fields)
        )

    async def list_subscriptions(
        self, company_id: uuid.UUID
    ) -> List[CompanyProductSubscription]:
        result = await self._s.execute(
            select(CompanyProductSubscription)
            .where(CompanyProductSubscription.company_id == company_id)
            .order_by(CompanyProductSubscription.assigned_at.desc())
        )
        return list(result.scalars().all())

    # ── Tier ──────────────────────────────────────────────────────────────────

    async def get_tier_by_id(self, tier_id: uuid.UUID) -> Optional[Tier]:
        result = await self._s.execute(
            select(Tier).where(Tier.id == tier_id)
        )
        return result.scalar_one_or_none()

    async def list_tiers(self) -> List[Tier]:
        result = await self._s.execute(
            select(Tier)
            .where(Tier.is_active == True)
            .order_by(Tier.name)
        )
        return list(result.scalars().all())

    # ── User ──────────────────────────────────────────────────────────────────

    async def list_users(self) -> List[User]:
        result = await self._s.execute(
            select(User)
            .where(User.deleted_at == None)
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self._s.execute(
            select(User).where(
                User.id         == user_id,
                User.deleted_at == None,
            )
        )
        return result.scalar_one_or_none()