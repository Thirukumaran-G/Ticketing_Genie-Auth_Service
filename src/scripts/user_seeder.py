"""
Seeds support agents and team leads, sends welcome email to each.
Run via:
    uv run python -m src.scripts.staff_seeder
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.models import Role, User
from src.core.services.email_service_welcome import EmailService
from src.observability.logging.logger import get_logger
from src.utils.password_utils import generate_secure_password, hash_password

logger     = get_logger(__name__)
_email_svc = EmailService()

# ── Staff to seed ─────────────────────────────────────────────────────────────
STAFF: list[dict] = [
    {"email": "vimalsrinivasansn@gmail.com",          "full_name": "Vimal Srinivasan",  "role": "agent"},
    {"email": "j.d.rudresh@gmail.com",                "full_name": "Rudresh JD",        "role": "agent"},
    {"email": "sylendravinayak@gmail.com",             "full_name": "Sylendra Vinayak",  "role": "agent"},
    {"email": "larwinj4683@gmail.com",                 "full_name": "Larwin J",          "role": "agent"},
    {"email": "kishoreshankar870@gmail.com",           "full_name": "Kishore Shankar",   "role": "agent"},
    {"email": "baranekumar56@gmail.com",               "full_name": "Barane Kumar",      "role": "agent"},
    {"email": "mithunprabha82@gmail.com",              "full_name": "Mithun Prabha",     "role": "agent"},
    {"email": "pragateesh.g2022ai-ds@sece.ac.in",     "full_name": "Pragateesh G",      "role": "agent"},
    {"email": "thirukumaran.g2022ai-ds@sece.ac.in",   "full_name": "Thirukumaran G",    "role": "team_lead"},
    {"email": "gthirukumaranias96776@gmail.com",       "full_name": "Thirukumaran G",    "role": "team_lead"},
    {"email": "vetrivel.a2022ai-ds@sece.ac.in",       "full_name": "Vetrivel A",        "role": "team_lead"},
    {"email": "rudresh.jd2022ai-ds@sece.ac.in",       "full_name": "Rudresh JD",        "role": "team_lead"},
]
# ─────────────────────────────────────────────────────────────────────────────


async def seed() -> None:
    async with AsyncSessionFactory() as session:

        # pre-load roles
        agent_result = await session.execute(
            select(Role).where(Role.name == "agent", Role.is_active == True)
        )
        agent_role = agent_result.scalar_one_or_none()

        lead_result = await session.execute(
            select(Role).where(Role.name == "team_lead", Role.is_active == True)
        )
        lead_role = lead_result.scalar_one_or_none()

        if not agent_role or not lead_role:
            print("❌ Roles not found — run role_tier_seeder first.")
            return

        role_map = {
            "agent":     agent_role,
            "team_lead": lead_role,
        }

        print()
        for entry in STAFF:
            # skip if already exists
            existing = await session.execute(
                select(User).where(User.email == entry["email"])
            )
            if existing.scalar_one_or_none():
                print(f"   ⚠️  Already exists : {entry['email']}")
                continue

            role      = role_map[entry["role"]]
            # temp_pass = generate_secure_password(length=12)
            temp_pass = "Vasanthi1981@"

            user = User(
                email=entry["email"],
                hashed_password=hash_password(temp_pass),
                full_name=entry["full_name"],
                role_id=role.id,
                is_active=True,
            )
            session.add(user)
            await session.flush()   # get user.id before email

            # send welcome email
            try:
                _email_svc.send_welcome_credentials(
                    to_email=entry["email"],
                    full_name=entry["full_name"],
                    role=entry["role"],
                    temp_password=temp_pass,
                )
                mail_status = "📧 email sent"
            except Exception as exc:
                logger.error("welcome_email_failed", email=entry["email"], error=str(exc))
                mail_status = "⚠️  email failed"

            logger.info("staff_seeded", email=entry["email"], role=entry["role"])
            print(f"   ✅ {entry['role']:<12} {entry['email']:<45} {mail_status}")

        await session.commit()
        print("\n✅ Staff seeding complete.\n")


if __name__ == "__main__":
    asyncio.run(seed())