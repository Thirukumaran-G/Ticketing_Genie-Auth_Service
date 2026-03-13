from __future__ import annotations

import asyncio

from sqlalchemy import text

from src.data.clients.postgres_client import AsyncSessionFactory
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)

PRODUCTS = [
    {
        "name": "GTK-FUNDS",
        "code": "PROD-001",
        "description": (
            "GTK-FUNDS is a financial transaction and fund management platform. "
            "It handles payments, fund transfers, ledger entries, and reconciliation. "
            "Issues related to payment failures, transaction errors, fund disbursement delays, "
            "or ledger discrepancies are considered high to critical severity."
        ),
    },
    {
        "name": "Grocenow",
        "code": "PROD-002",
        "description": (
            "Grocenow is an online grocery delivery platform connecting customers with "
            "local stores for same-day delivery. "
            "Issues related to order placement, delivery tracking, inventory sync, "
            "or checkout failures directly impact customer experience and are high severity."
        ),
    },
    {
        "name": "Ecommerce-Bot",
        "code": "PROD-003",
        "description": (
            "Ecommerce-Bot is an AI-powered chatbot and automation platform for e-commerce stores. "
            "It handles customer queries, order status, returns, and product recommendations. "
            "Issues with bot unavailability, incorrect responses, or broken integrations "
            "affect customer support operations and are medium to high severity."
        ),
    },
]


async def seed() -> None:
    async with AsyncSessionFactory() as session:
        for entry in PRODUCTS:
            existing = await session.execute(
                text("SELECT id FROM auth.product WHERE code = :code"),
                {"code": entry["code"]},
            )
            if existing.fetchone():
                logger.info("product_exists", code=entry["code"])
                print(f"Already exists : {entry['name']} ({entry['code']})")
                continue

            await session.execute(
                text(
                    """
                    INSERT INTO auth.product (id, name, code, description, is_active)
                    VALUES (gen_random_uuid(), :name, :code, :description, TRUE)
                    """
                ),
                {
                    "name":        entry["name"],
                    "code":        entry["code"],
                    "description": entry["description"],
                },
            )
            logger.info("product_seeded", name=entry["name"], code=entry["code"])
            print(f"Seeded : {entry['name']} ({entry['code']})")

        await session.commit()
        print("\nProduct seeding complete.\n")


if __name__ == "__main__":
    asyncio.run(seed())