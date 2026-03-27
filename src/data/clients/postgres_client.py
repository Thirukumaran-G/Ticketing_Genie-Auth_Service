from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import settings

# ── Primary engine — writes and general reads ─────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={"server_settings": {"search_path": "auth"}},
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

fresh_read_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=2,
    max_overflow=5,
    pool_pre_ping=True,
    execution_options={"isolation_level": "AUTOCOMMIT"},
    connect_args={"server_settings": {"search_path": "auth"}},
)

FreshReadSessionFactory = async_sessionmaker(
    bind=fresh_read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Standard session — full transaction control for writes and normal reads."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_fresh_read_session() -> AsyncGenerator[AsyncSession, None]:
    async with FreshReadSessionFactory() as session:
        try:
            yield session
        except Exception:
            raise
        finally:
            await session.close()
