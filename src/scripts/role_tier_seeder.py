"""
Run via:
    uv run python -m src.scripts.role_tier_seeder
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.models import Role, Tier
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)

ROLES = [
    {"name": "customer",  "description": "End-user customer belonging to a company"},
    {"name": "agent",     "description": "Support agent"},
    {"name": "team_lead", "description": "Support team lead"},
    {"name": "admin",     "description": "Platform administrator"},
]

TIERS = [
    {"name": "starter",    "description": "Starter tier"},
    {"name": "standard",   "description": "Standard tier"},
    {"name": "enterprise", "description": "Enterprise tier"},
]


async def seed() -> None:
    async with AsyncSessionFactory() as session:
        for role_data in ROLES:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if not result.scalar_one_or_none():
                session.add(Role(**role_data, is_active=True))
                logger.info("role_seeded", name=role_data["name"])
            else:
                logger.info("role_exists", name=role_data["name"])

        for tier_data in TIERS:
            result = await session.execute(
                select(Tier).where(Tier.name == tier_data["name"])
            )
            if not result.scalar_one_or_none():
                session.add(Tier(**tier_data, is_active=True))
                logger.info("tier_seeded", name=tier_data["name"])
            else:
                logger.info("tier_exists", name=tier_data["name"])

        await session.commit()
        logger.info("seeding_complete")


if __name__ == "__main__":
    asyncio.run(seed())