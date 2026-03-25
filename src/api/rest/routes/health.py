from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="auth-service")


# @router.post("/admin/reseed", include_in_schema=False)
# async def reseed():
#     """TEMPORARY - remove after use"""
#     from sqlalchemy import text
#     from src.data.clients.postgres_client import engine
#     from src.scripts.role_tier_seeder import seed as tier_seeder
#     from src.scripts.company_seeder import seed as company_seeder
#     from src.scripts.product_seeder import seed as product_seeder
#     from src.scripts.admin_seeder import seed as admin_seeder
#     from src.scripts.user_seeder import seed as user_seeder
#     from src.scripts.subscription_seeder import seed as subscription_seeder

#     # Wipe
#     async with engine.begin() as conn:
#         await conn.execute(text("DROP SCHEMA auth CASCADE"))
#         await conn.execute(text("CREATE SCHEMA auth"))

#     # Recreate tables
#     from src.data.models.postgres.models import Base
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

#     # Reseed in order
#     await tier_seeder()
#     await company_seeder()
#     await product_seeder()
#     await admin_seeder()
#     await user_seeder()
#     await subscription_seeder()

#     return {"status": "reseeded successfully"}
