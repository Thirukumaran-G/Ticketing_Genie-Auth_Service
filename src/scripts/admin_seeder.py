from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.models import Role, User
from src.observability.logging.logger import get_logger
from src.utils.password_utils import hash_password
from src.config.settings import settings

logger = get_logger(__name__)

ADMIN_EMAIL    = settings.ADMIN_EMAIL
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
ADMIN_FULLNAME = settings.ADMIN_FULLNAME

async def seed() -> None:
    async with AsyncSessionFactory() as session:

        role_result = await session.execute(    
            select(Role).where(Role.name == "admin", Role.is_active == True)
        )
        role = role_result.scalar_one_or_none()
        if not role:
            logger.error("admin_role_not_found — run role_tier_seeder first")
            return

        user_result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        existing = user_result.scalar_one_or_none()
        if existing:
            logger.info("admin_already_exists", email=ADMIN_EMAIL)
            return

        admin = User(
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name=ADMIN_FULLNAME,
            role_id=role.id,
            is_active=True,
        )
        session.add(admin)
        await session.commit()

        logger.info("admin_seeded", email=ADMIN_EMAIL)
        print(f"\n✅ Admin seeded successfully.")
        print(f"   Email    : {ADMIN_EMAIL}")
        print(f"   Password : {ADMIN_PASSWORD}")
        print(f"   ⚠️  Change this password after first login!\n")


if __name__ == "__main__":
    asyncio.run(seed())