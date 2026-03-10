from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.models import PasswordResetToken


class PasswordResetRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, reset: PasswordResetToken) -> PasswordResetToken:
        self._s.add(reset)
        await self._s.flush()
        return reset

    async def get_valid_token(self, token_hash: str) -> Optional[PasswordResetToken]:
        result = await self._s.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.is_used    == False,
                PasswordResetToken.expires_at >  datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_existing(self, user_id: uuid.UUID) -> None:
        await self._s.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id  == user_id,
                PasswordResetToken.is_used  == False,
            )
            .values(is_used=True, used_at=datetime.now(timezone.utc))
        )

    async def mark_used(self, reset_id: uuid.UUID) -> None:
        await self._s.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == reset_id)
            .values(is_used=True, used_at=datetime.now(timezone.utc))
        )