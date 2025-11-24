import asyncio
import logging
from functools import wraps

from sqlalchemy import event
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite+aiosqlite:///./chitchats.db"

# Configure engine with WAL mode and increased timeout for better concurrency
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # Disable connection pooling for SQLite
    connect_args={
        "timeout": 30,  # Increase timeout to 30 seconds
        "check_same_thread": False,
    },
)


# Enable WAL mode for better concurrent access
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds in milliseconds
    cursor.close()


async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


def retry_on_db_lock(max_retries=5, initial_delay=0.1, backoff_factor=2):
    """
    Decorator to retry database operations on lock errors.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, DBAPIError) as e:
                    # Check if it's a database locked error
                    if "database is locked" in str(e).lower():
                        last_exception = e
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Database locked on attempt {attempt + 1}/{max_retries} "
                                f"for {func.__name__}, retrying in {delay}s..."
                            )
                            await asyncio.sleep(delay)
                            delay *= backoff_factor
                        else:
                            logger.error(f"Database locked after {max_retries} attempts for {func.__name__}")
                    else:
                        # Re-raise if it's not a lock error
                        raise
                except Exception:
                    # Re-raise any other exceptions immediately
                    raise

            # If we exhausted all retries, raise the last exception
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def get_db():
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
