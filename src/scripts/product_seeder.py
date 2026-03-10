from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.models import Product
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)

PRODUCTS = [
    {"name": "GTK-FUNDS","code": "PROD-001"},
    {"name": "Grocenow","code": "PROD-002"},
    {"name": "Ecommerce-Bot","code": "PROD-003"},
]


async def seed() -> None:
    async with AsyncSessionFactory() as session:
        for entry in PRODUCTS:
            existing = await session.execute(
                select(Product).where(Product.code == entry["code"])
            )
            if existing.scalar_one_or_none():
                logger.info("product_exists", code=entry["code"])
                print(f"Already exists : {entry['name']} ({entry['code']})")
                continue

            product = Product(
                name=entry["name"],
                code=entry["code"],
                is_active=True,
            )
            session.add(product)
            logger.info("product_seeded", name=entry["name"], code=entry["code"])
            print(f"Seeded : {entry['name']} ({entry['code']})")

        await session.commit()
        print("\nProduct seeding complete.\n")


if __name__ == "__main__":
    asyncio.run(seed())