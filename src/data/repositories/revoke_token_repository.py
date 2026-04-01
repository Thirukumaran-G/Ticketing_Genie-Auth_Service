from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.models import RevokeToken


class RevokeTokenRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, token: RevokeToken) -> RevokeToken:
        self._s.add(token)
        await self._s.flush()
        return token

    async def get_by_jti(self, jti: str) -> RevokeToken | None:
        result = await self._s.execute(
            select(RevokeToken).where(RevokeToken.jti == jti)
        )
        return result.scalar_one_or_none()

    async def revoke_by_jti(self, jti: str) -> None:
        await self._s.execute(
            update(RevokeToken)
            .where(RevokeToken.jti == jti)
            .values(is_revoked=True, revoked_at=datetime.now(UTC))
        )

    async def revoke_family(self, family_id: str) -> None:
        """Revoke all tokens in a family — called on theft detection or logout."""
        await self._s.execute(
            update(RevokeToken)
            .where(
                RevokeToken.family_id  == family_id,
                RevokeToken.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all active tokens for a user — called on password reset."""
        await self._s.execute(
            update(RevokeToken)
            .where(
                RevokeToken.user_id    == user_id,
                RevokeToken.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=datetime.now(UTC))
        )
