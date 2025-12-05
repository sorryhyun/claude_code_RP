#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL.

Usage:
    # First, install aiosqlite temporarily if not present
    uv pip install aiosqlite

    # Then run the migration
    python scripts/migrate_sqlite_to_postgres.py

Prerequisites:
    1. SQLite database file exists at backend/chitchats.db
    2. PostgreSQL database is running and accessible
    3. DATABASE_URL environment variable is set
    4. Tables are already created in PostgreSQL (run backend first)

The script will:
    1. Read all data from SQLite
    2. Transfer all records with proper type conversions
    3. Convert Integer booleans (0/1) to native PostgreSQL booleans
    4. Reset PostgreSQL sequences for auto-increment columns
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    import aiosqlite
except ImportError:
    print("Error: aiosqlite not installed. Run: uv pip install aiosqlite")
    sys.exit(1)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

SQLITE_PATH = backend_path / "chitchats.db"
POSTGRES_URL = os.getenv("DATABASE_URL")


async def migrate_table(
    sqlite_conn: aiosqlite.Connection,
    pg_conn,
    table_name: str,
    bool_columns: list[str] | None = None,
) -> int:
    """
    Migrate a single table from SQLite to PostgreSQL.

    Args:
        sqlite_conn: SQLite database connection
        pg_conn: PostgreSQL connection
        table_name: Name of the table to migrate
        bool_columns: List of column names that need int->bool conversion

    Returns:
        Number of rows migrated
    """
    bool_columns = bool_columns or []

    print(f"  Migrating {table_name}...")

    # Get all rows from SQLite
    cursor = await sqlite_conn.execute(f"SELECT * FROM {table_name}")
    rows = await cursor.fetchall()

    if not rows:
        print(f"    No rows to migrate in {table_name}")
        return 0

    # Get column names
    columns = [description[0] for description in cursor.description]

    migrated = 0
    for row in rows:
        values = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Convert integer booleans to Python booleans
            if col in bool_columns:
                value = bool(value) if value is not None else False
            values[col] = value

        # Build INSERT statement with ON CONFLICT DO NOTHING
        cols = ', '.join(f'"{c}"' for c in columns)
        placeholders = ', '.join(f':{c}' for c in columns)

        try:
            await pg_conn.execute(
                text(f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'),
                values
            )
            migrated += 1
        except Exception as e:
            print(f"    Warning: Error inserting row into {table_name}: {e}")

    print(f"    Migrated {migrated}/{len(rows)} rows from {table_name}")
    return migrated


async def reset_sequence(pg_conn, table_name: str, id_column: str = "id"):
    """Reset PostgreSQL sequence for auto-increment column."""
    try:
        await pg_conn.execute(text(f"""
            SELECT setval(
                pg_get_serial_sequence('{table_name}', '{id_column}'),
                COALESCE((SELECT MAX({id_column}) FROM {table_name}), 1)
            )
        """))
        print(f"    Reset sequence for {table_name}.{id_column}")
    except Exception as e:
        print(f"    Warning: Could not reset sequence for {table_name}: {e}")


async def migrate():
    """Main migration function."""
    if not SQLITE_PATH.exists():
        print(f"Error: SQLite database not found at {SQLITE_PATH}")
        print("Make sure the backend has been run at least once with SQLite.")
        sys.exit(1)

    if not POSTGRES_URL:
        print("Error: DATABASE_URL environment variable not set")
        print("Set it in .env file: DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname")
        sys.exit(1)

    print(f"SQLite source: {SQLITE_PATH}")
    print(f"PostgreSQL target: {POSTGRES_URL.split('@')[1] if '@' in POSTGRES_URL else POSTGRES_URL}")
    print()

    # Connect to SQLite
    sqlite_conn = await aiosqlite.connect(SQLITE_PATH)
    sqlite_conn.row_factory = aiosqlite.Row

    # Connect to PostgreSQL
    pg_engine = create_async_engine(POSTGRES_URL, echo=False)

    try:
        async with pg_engine.begin() as pg_conn:
            print("Starting migration...")
            print()

            # Migrate tables in order (respecting foreign key dependencies)

            # 1. Rooms (has is_paused boolean)
            await migrate_table(
                sqlite_conn, pg_conn, 'rooms',
                bool_columns=['is_paused']
            )
            await reset_sequence(pg_conn, 'rooms')

            # 2. Agents (has is_critic boolean)
            await migrate_table(
                sqlite_conn, pg_conn, 'agents',
                bool_columns=['is_critic']
            )
            await reset_sequence(pg_conn, 'agents')

            # 3. room_agents (association table, no auto-increment)
            await migrate_table(sqlite_conn, pg_conn, 'room_agents')

            # 4. room_agent_sessions (no auto-increment, composite key)
            await migrate_table(sqlite_conn, pg_conn, 'room_agent_sessions')

            # 5. Messages (largest table, no boolean columns)
            await migrate_table(sqlite_conn, pg_conn, 'messages')
            await reset_sequence(pg_conn, 'messages')

            print()
            print("Migration completed successfully!")
            print()
            print("Next steps:")
            print("  1. Verify data in PostgreSQL: psql -d chitchats -c 'SELECT COUNT(*) FROM rooms;'")
            print("  2. Back up and remove backend/chitchats.db if everything looks good")

    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        await sqlite_conn.close()
        await pg_engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    print()
    asyncio.run(migrate())
