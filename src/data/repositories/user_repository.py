from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.models import Company, CompanyProductSubscription, Product, Role, Tier, User


class UserRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── User lookups ──────────────────────────────────────────────────────────

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._s.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: str | uuid.UUID) -> Optional[User]:
        result = await self._s.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,
                User.deleted_at == None,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._s.add(user)
        await self._s.flush()
        return user

    async def update_fields(self, user_id: uuid.UUID, fields: Dict[str, Any]) -> None:
        await self._s.execute(
            update(User).where(User.id == user_id).values(**fields)
        )

    # ── Role ──────────────────────────────────────────────────────────────────

    async def get_role_by_name(self, name: str) -> Optional[Role]:
        result = await self._s.execute(select(Role).where(Role.name == name, Role.is_active == True))
        return result.scalar_one_or_none()

    async def get_role_name_by_id(self, role_id: uuid.UUID) -> Optional[str]:
        result = await self._s.execute(select(Role.name).where(Role.id == role_id))
        return result.scalar_one_or_none()

    # company domain lookup 

    async def get_company_by_domain(self, domain: str) -> Optional[Company]:
        result = await self._s.execute(
            select(Company).where(Company.domain == domain, Company.is_active == True)
        )
        return result.scalar_one_or_none()

    # ── Product tiers via CompanyProductSubscription ──────────────────────────

    async def get_product_tiers_for_company(
        self, company_id: uuid.UUID
    ) -> Dict[str, Dict[str, str]]:
        """
        Returns { "<product_id>": { "tier_id": "...", "tier_name": "...", "code": "..." } }
        for all active subscriptions of the given company.
        """
        result = await self._s.execute(
            select(
                CompanyProductSubscription.product_id,
                CompanyProductSubscription.tier_id,
                Tier.name.label("tier_name"),
                Product.code.label("product_code"),
            )
            .join(Tier,    Tier.id    == CompanyProductSubscription.tier_id)
            .join(Product, Product.id == CompanyProductSubscription.product_id)
            .where(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.is_active  == True,
                Product.is_active == True,
            )
        )
        rows = result.all()
        return {
            str(row.product_id): {
                "tier_id":   str(row.tier_id),
                "tier_name": row.tier_name,
                "code":      row.product_code,
            }
            for row in rows
        }

    # ── Tier ──────────────────────────────────────────────────────────────────

    async def get_tier_by_name(self, name: str) -> Optional[Tier]:
        result = await self._s.execute(select(Tier).where(Tier.name == name, Tier.is_active == True))
        return result.scalar_one_or_none()