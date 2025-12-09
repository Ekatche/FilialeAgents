"""
Database configuration and session management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from core.config import settings

# Create async engine with Supabase-optimized pool settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=settings.DB_POOL_SIZE,  # Number of persistent connections
    max_overflow=settings.DB_MAX_OVERFLOW,  # Additional connections in peak times
    pool_timeout=settings.DB_POOL_TIMEOUT,  # Timeout to get a connection
    pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle connections after 1 hour
    poolclass=NullPool if "sqlite" in settings.DATABASE_URL else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Usage in FastAPI:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    This should be called on application startup.
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with Base
        from models import db_models  # noqa: F401

        # Create all tables
        # Disabled to prevent conflicts with Alembic migrations (DuplicateObjectError on Enums)
        # Schema management should be done via Alembic
        # await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    This should be called on application shutdown.
    """
    await engine.dispose()
