# Auth service
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from src.api.middleware.cors import setup_cors
from src.api.middleware.error_handler import setup_error_handlers
from src.api.middleware.trusedhost import setup_trusted_hosts
from src.api.rest.routes.admin_router import router as admin_router
from src.api.rest.routes.auth_routes import router as auth_router
from src.api.rest.routes.health import router as health_router
from src.api.rest.routes.internal_routers import router as internal_router
from src.data.clients.postgres_client import engine, get_db_session
from src.data.models.postgres.models import Base
from src.observability.logging.logger import configure_logging, get_logger
from src.scripts.admin_seeder import seed as admin_seeder
from src.scripts.company_seeder import seed as company_seeder
from src.scripts.product_seeder import seed as product_seeder
from src.scripts.role_tier_seeder import seed as tier_seeder
from src.scripts.subscription_seeder import seed as subscription_seeder
from src.scripts.user_seeder import seed as user_seeder

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup tasks before the app begins serving requests."""
    logger.info("auth_service_starting")

    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    # Seed roles and tiers
    async for _session in get_db_session():
        # await tier_seeder()
        # await company_seeder()
        # await product_seeder()
        # await admin_seeder()
        # await user_seeder()
        # await subscription_seeder()
        logger.info("roles_seeded")
        logger.info("tiers_seeded")
        break

    logger.info("auth_service_ready")
    yield
    logger.info("auth_service_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="Ticketing Genie — Auth Service",
        description="Authentication and authorization microservice.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    # ── Custom OpenAPI schema ─────────────────────────────────────────────────
    def custom_openapi() -> dict[str, Any]:
        """HTTPBearer on all non-Authentication-tagged operations."""
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
        openapi_schema["components"]["securitySchemes"]["HTTPBearer"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token from /auth/login",
        }

        http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}

        for _path, path_item in openapi_schema.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in list(path_item.items()):
                if method.lower() not in http_methods:
                    continue
                if not isinstance(operation, dict):
                    continue

                tags = operation.get("tags", [])
                if tags and tags[0] == "Authentication":
                    continue

                if "security" in operation:
                    existing = operation["security"]
                    if not any("HTTPBearer" in sec for sec in existing):
                        existing.append({"HTTPBearer": []})
                    operation["security"] = existing
                else:
                    operation["security"] = [{"HTTPBearer": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    # ── Middleware ────────────────────────────────────────────────────────────
    setup_trusted_hosts(app)
    setup_cors(app)
    setup_error_handlers(app)

    prefix="/api/v1/auth"
    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(internal_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)

    return app
