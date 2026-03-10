from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.models import Company, CompanyProductSubscription, Product, Tier
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)

SUBSCRIPTIONS: dict[str, list[tuple[str, str]]] = {
    "genworx.ai": [
        ("PROD-002", "enterprise"),
        ("PROD-001", "standard"),
        ("PROD-003", "starter"),
    ],
}


async def seed() -> None:
    async with AsyncSessionFactory() as session:

        for domain, assignments in SUBSCRIPTIONS.items():

            # resolve company
            company_result = await session.execute(
                select(Company).where(
                    Company.domain    == domain,
                    Company.is_active == True,
                )
            )
            company = company_result.scalar_one_or_none()
            if not company:
                logger.error("company_not_found", domain=domain)
                print(f"   ❌ Company not found for domain: {domain} — run company_seeder first")
                continue

            print(f"\n   Company : {company.name} ({domain})")

            for product_code, tier_name in assignments:

                # resolve product
                product_result = await session.execute(
                    select(Product).where(
                        Product.code      == product_code,
                        Product.is_active == True,
                    )
                )
                product = product_result.scalar_one_or_none()
                if not product:
                    logger.error("product_not_found", code=product_code)
                    print(f"      ❌ Product not found: {product_code} — run product_seeder first")
                    continue

                # resolve tier
                tier_result = await session.execute(
                    select(Tier).where(
                        Tier.name      == tier_name,
                        Tier.is_active == True,
                    )
                )
                tier = tier_result.scalar_one_or_none()
                if not tier:
                    logger.error("tier_not_found", name=tier_name)
                    print(f"      ❌ Tier not found: {tier_name} — run role_tier_seeder first")
                    continue

                # check already active subscription
                existing_result = await session.execute(
                    select(CompanyProductSubscription).where(
                        CompanyProductSubscription.company_id == company.id,
                        CompanyProductSubscription.product_id == product.id,
                        CompanyProductSubscription.is_active  == True,
                    )
                )
                if existing_result.scalar_one_or_none():
                    logger.info("subscription_exists",
                                company=domain,
                                product=product_code)
                    print(f"      ⚠️  Already exists : {product_code} → {tier_name}")
                    continue

                sub = CompanyProductSubscription(
                    company_id=company.id,
                    product_id=product.id,
                    tier_id=tier.id,
                    is_active=True,
                )
                session.add(sub)
                logger.info("subscription_seeded",
                            company=domain,
                            product=product_code,
                            tier=tier_name)
                print(f"      ✅ Assigned : {product_code} → {tier_name}")

        await session.commit()
        print("\n✅ Subscription seeding complete.\n")


if __name__ == "__main__":
    asyncio.run(seed())