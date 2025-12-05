"""
Database configuration for PostgreSQL.

This module provides the database engine, session maker, and initialization functions
for the application's PostgreSQL database.
"""

import logging

from core import get_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Get settings for database configuration
settings = get_settings()

# Configure PostgreSQL engine with connection pooling
# Note: async engines automatically use AsyncAdaptedQueuePool
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,  # Verify connections before use
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    """
    Dependency that yields database sessions.

    Yields:
        AsyncSession: Database session for the request
    """
    async with async_session_maker() as session:
        yield session


async def init_db():
    """
    Initialize database schema and run migrations.

    This function:
    1. Creates all tables if they don't exist (for fresh installs)
    2. Runs migrations to add missing columns (for upgrades)
    """
    # Import here to avoid circular dependency
    from utils.migrations import run_migrations

    # Create any missing tables first (for fresh installs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Then run migrations to add any missing columns to existing tables
    await run_migrations(engine)
