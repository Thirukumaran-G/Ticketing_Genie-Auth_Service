from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.models import User
from src.schemas.auth_schemas import (
    InternalCustomerCreateRequest,
    InternalCustomerCreateResponse,
    PreferredContactUpdate,
)
from src.utils.password_utils import generate_secure_password, hash_password

from src.data.repositories.internal_repository import InternalRepository

try:
    import uuid6
except ImportError:
    uuid6 = None  # type: ignore[assignment]


class InternalAuthService:
    """Handles business logic for all /internal/* endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = InternalRepository(session)

    # ── User ──────────────────────────────────────────────────────────────────

    async def get_user_with_role(self, user_id: str) -> dict:
        user = await self._repo.get_user_by_id(uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=404)

        role = await self._repo.get_role_by_id(user.role_id) if user.role_id else None
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": role.name if role else None,
            "is_active": user.is_active,
            "preferred_contact": user.preferred_contact,
        }

    async def set_preferred_contact(
        self, user_id: uuid.UUID, payload: PreferredContactUpdate
    ) -> None:
        user = await self._repo.update_user_preferred_contact(
            user_id, payload.preferred_contact
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    # ── Tier ──────────────────────────────────────────────────────────────────

    async def get_tier_by_name(self, tier_name: str) -> dict:
        tier = await self._repo.get_tier_by_name(tier_name)
        if not tier:
            raise HTTPException(
                status_code=404, detail=f"Tier '{tier_name}' not found"
            )
        return {"tier_id": str(tier.id), "tier_name": tier.name}

    async def get_customer_tier(
        self,
        user_id: uuid.UUID,
        product_id: Optional[uuid.UUID] = None,
    ) -> dict:
        user = await self._repo.get_active_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Customer not found")
        if not user.company_id:
            raise HTTPException(
                status_code=404, detail="Customer has no associated company"
            )

        row = await self._repo.get_customer_tier(user.company_id, product_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No active product subscription found for this customer",
            )
        _, tier = row
        return {"tier_id": str(tier.id), "tier_name": tier.name}

    # ── Company ───────────────────────────────────────────────────────────────

    async def get_company_by_domain(self, domain: str) -> dict:
        company = await self._repo.get_company_by_domain(domain)
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"No active company for domain '{domain}'",
            )
        return {
            "company_id": str(company.id),
            "company_name": company.name,
            "domain": company.domain or domain,
        }

    # ── Product ───────────────────────────────────────────────────────────────

    async def list_active_products(self) -> dict:
        products = await self._repo.list_active_products()
        return {
            "products": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "code": p.code,
                    "description": p.description,
                }
                for p in products
            ]
        }

    # ── Customer create-or-get ────────────────────────────────────────────────

    async def create_or_get_customer(
        self, payload: InternalCustomerCreateRequest
    ) -> InternalCustomerCreateResponse:
        existing = await self._repo.get_active_user_by_email(payload.email)
        if existing:
            return InternalCustomerCreateResponse(
                user_id=str(existing.id),
                email=existing.email,
                full_name=existing.full_name or "",
                temp_password="",
                is_new=False,
            )

        role = await self._repo.get_role_by_name("customer")
        if not role:
            raise HTTPException(
                status_code=500,
                detail="Customer role not found — run seeder.",
            )

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
        saved = await self._repo.save_user(new_user)

        return InternalCustomerCreateResponse(
            user_id=str(saved.id),
            email=saved.email,
            full_name=saved.full_name or "",
            temp_password=temp_password,
            is_new=True,
        )