"""
Seeds a sample company with domain extracted from an example email.
Run via:
    uv run python -m src.scripts.company_seeder
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.models import Company
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)

# ── Add your companies here ───────────────────────────────────────────────────
COMPANIES = [
    {
        "email":  "thirukumarang@genworx.ai",
        "name":   "Genworx",
    },
]
# ─────────────────────────────────────────────────────────────────────────────


def _extract_domain(email: str) -> str:
    return email.split("@", 1)[1].lower()


async def seed() -> None:
    async with AsyncSessionFactory() as session:
        for entry in COMPANIES:
            domain = _extract_domain(entry["email"])

            existing = await session.execute(
                select(Company).where(Company.domain == domain)
            )
            if existing.scalar_one_or_none():
                logger.info("company_exists", domain=domain)
                print(f"   ⚠️  Already exists : {domain}")
                continue

            company = Company(
                name=entry["name"],
                domain=domain,
                is_active=True,
            )
            session.add(company)
            logger.info("company_seeded", name=entry["name"], domain=domain)
            print(f"   ✅ Seeded : {entry['name']} ({domain})")

        await session.commit()
        print("\n✅ Company seeding complete.\n")


if __name__ == "__main__":
    asyncio.run(seed())
