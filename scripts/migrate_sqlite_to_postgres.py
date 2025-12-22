#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL for ChitChats.

Usage:
    python scripts/migrate_sqlite_to_postgres.py

This script:
1. Creates PostgreSQL tables using SQLAlchemy models
2. Reads all data from SQLite
3. Inserts data into PostgreSQL with proper ordering (respecting foreign keys)
"""

import asyncio
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import asyncpg


def parse_datetime(value):
    """Parse datetime string from SQLite to Python datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Try common datetime formats
    for fmt in [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# Configuration
SQLITE_PATH = Path(__file__).parent.parent / "backend" / "chitchats.db"
POSTGRES_URL = "postgresql://postgres:postgres@localhost:5432/chitchats"


async def main():
    print("🚀 Starting SQLite to PostgreSQL migration...")

    # Connect to SQLite
    print(f"📂 Reading from SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    # Connect to PostgreSQL
    print("🐘 Connecting to PostgreSQL...")
    pg_conn = await asyncpg.connect(POSTGRES_URL)

    try:
        # Create tables in PostgreSQL
        print("📋 Creating PostgreSQL tables...")
        await create_tables(pg_conn)

        # Migrate data in order (respecting foreign keys)
        print("\n📦 Migrating data...")

        # 1. Agents (no dependencies)
        await migrate_agents(sqlite_conn, pg_conn)

        # 2. Rooms (no dependencies)
        await migrate_rooms(sqlite_conn, pg_conn)

        # 3. Messages (depends on rooms, agents)
        await migrate_messages(sqlite_conn, pg_conn)

        # 4. Room-Agent associations (depends on rooms, agents)
        await migrate_room_agents(sqlite_conn, pg_conn)

        # 5. Room-Agent sessions (depends on rooms, agents)
        await migrate_room_agent_sessions(sqlite_conn, pg_conn)

        # Reset sequences to max id + 1
        print("\n🔄 Resetting sequences...")
        await reset_sequences(pg_conn)

        print("\n✅ Migration completed successfully!")

        # Verify counts
        print("\n📊 Verification:")
        await verify_migration(sqlite_conn, pg_conn)

    finally:
        sqlite_conn.close()
        await pg_conn.close()


async def create_tables(pg_conn):
    """Create all tables in PostgreSQL."""
    await pg_conn.execute("""
        -- Agents table
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL UNIQUE,
            "group" VARCHAR,
            config_file VARCHAR,
            profile_pic TEXT,
            in_a_nutshell TEXT,
            characteristics TEXT,
            recent_events TEXT,
            system_prompt TEXT NOT NULL,
            is_critic BOOLEAN DEFAULT FALSE,
            interrupt_every_turn BOOLEAN DEFAULT FALSE,
            priority INTEGER DEFAULT 0,
            transparent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Rooms table
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            owner_id VARCHAR,
            name VARCHAR NOT NULL,
            max_interactions INTEGER,
            is_paused BOOLEAN DEFAULT FALSE,
            is_finished BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_read_at TIMESTAMP
        );

        -- Messages table
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
            content TEXT NOT NULL,
            role VARCHAR NOT NULL,
            participant_type VARCHAR,
            participant_name VARCHAR,
            thinking TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_data TEXT,
            image_media_type VARCHAR
        );

        -- Room-Agent association table
        CREATE TABLE IF NOT EXISTS room_agents (
            room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            joined_at TIMESTAMP,
            PRIMARY KEY (room_id, agent_id)
        );

        -- Room-Agent sessions table
        CREATE TABLE IF NOT EXISTS room_agent_sessions (
            room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            session_id VARCHAR NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (room_id, agent_id)
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS ix_agents_id ON agents(id);
        CREATE INDEX IF NOT EXISTS ix_agents_name ON agents(name);
        CREATE INDEX IF NOT EXISTS idx_agents_group ON agents("group");
        CREATE INDEX IF NOT EXISTS ix_rooms_id ON rooms(id);
        CREATE INDEX IF NOT EXISTS ix_rooms_name ON rooms(name);
        CREATE INDEX IF NOT EXISTS ix_rooms_owner_id ON rooms(owner_id);
        CREATE INDEX IF NOT EXISTS ix_rooms_last_activity_at ON rooms(last_activity_at);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_rooms_owner_name ON rooms(owner_id, name);
        CREATE INDEX IF NOT EXISTS ix_messages_id ON messages(id);
        CREATE INDEX IF NOT EXISTS idx_message_room_id ON messages(room_id);
        CREATE INDEX IF NOT EXISTS idx_message_agent_id ON messages(agent_id);
        CREATE INDEX IF NOT EXISTS idx_message_room_timestamp ON messages(room_id, timestamp);
    """)
    print("  ✓ Tables created")


async def migrate_agents(sqlite_conn, pg_conn):
    """Migrate agents table."""
    cursor = sqlite_conn.execute("SELECT * FROM agents ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("  ⚠ No agents to migrate")
        return

    for row in rows:
        await pg_conn.execute(
            """
            INSERT INTO agents (id, name, "group", config_file, profile_pic,
                              in_a_nutshell, characteristics, recent_events,
                              system_prompt, is_critic, interrupt_every_turn,
                              priority, transparent, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (id) DO NOTHING
        """,
            row["id"],
            row["name"],
            row["group"],
            row["config_file"],
            row["profile_pic"],
            row["in_a_nutshell"],
            row["characteristics"],
            row["recent_events"],
            row["system_prompt"],
            bool(row["is_critic"]) if row["is_critic"] is not None else False,
            bool(row["interrupt_every_turn"]) if row["interrupt_every_turn"] is not None else False,
            row["priority"] or 0,
            bool(row["transparent"]) if row["transparent"] is not None else False,
            parse_datetime(row["created_at"]),
        )

    print(f"  ✓ Migrated {len(rows)} agents")


async def migrate_rooms(sqlite_conn, pg_conn):
    """Migrate rooms table."""
    cursor = sqlite_conn.execute("SELECT * FROM rooms ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("  ⚠ No rooms to migrate")
        return

    for row in rows:
        await pg_conn.execute(
            """
            INSERT INTO rooms (id, owner_id, name, max_interactions, is_paused,
                             is_finished, created_at, last_activity_at, last_read_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO NOTHING
        """,
            row["id"],
            row["owner_id"],
            row["name"],
            row["max_interactions"],
            bool(row["is_paused"]) if row["is_paused"] is not None else False,
            bool(row["is_finished"]) if row["is_finished"] is not None else False,
            parse_datetime(row["created_at"]),
            parse_datetime(row["last_activity_at"]),
            parse_datetime(row["last_read_at"]),
        )

    print(f"  ✓ Migrated {len(rows)} rooms")


async def migrate_messages(sqlite_conn, pg_conn):
    """Migrate messages table."""
    cursor = sqlite_conn.execute("SELECT * FROM messages ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("  ⚠ No messages to migrate")
        return

    for row in rows:
        await pg_conn.execute(
            """
            INSERT INTO messages (id, room_id, agent_id, content, role,
                                participant_type, participant_name, thinking,
                                timestamp, image_data, image_media_type)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (id) DO NOTHING
        """,
            row["id"],
            row["room_id"],
            row["agent_id"],
            row["content"],
            row["role"],
            row["participant_type"],
            row["participant_name"],
            row["thinking"],
            parse_datetime(row["timestamp"]),
            row["image_data"],
            row["image_media_type"],
        )

    print(f"  ✓ Migrated {len(rows)} messages")


async def migrate_room_agents(sqlite_conn, pg_conn):
    """Migrate room_agents association table."""
    cursor = sqlite_conn.execute("SELECT * FROM room_agents")
    rows = cursor.fetchall()

    if not rows:
        print("  ⚠ No room-agent associations to migrate")
        return

    migrated = 0
    for row in rows:
        try:
            await pg_conn.execute(
                """
                INSERT INTO room_agents (room_id, agent_id, joined_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (room_id, agent_id) DO NOTHING
            """,
                row["room_id"],
                row["agent_id"],
                parse_datetime(row["joined_at"]),
            )
            migrated += 1
        except Exception as e:
            print(f"    ⚠ Skipped room_agent ({row['room_id']}, {row['agent_id']}): {e}")

    print(f"  ✓ Migrated {migrated} room-agent associations")


async def migrate_room_agent_sessions(sqlite_conn, pg_conn):
    """Migrate room_agent_sessions table."""
    cursor = sqlite_conn.execute("SELECT * FROM room_agent_sessions")
    rows = cursor.fetchall()

    if not rows:
        print("  ⚠ No room-agent sessions to migrate")
        return

    migrated = 0
    for row in rows:
        try:
            await pg_conn.execute(
                """
                INSERT INTO room_agent_sessions (room_id, agent_id, session_id, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (room_id, agent_id) DO NOTHING
            """,
                row["room_id"],
                row["agent_id"],
                row["session_id"],
                parse_datetime(row["updated_at"]),
            )
            migrated += 1
        except Exception as e:
            print(f"    ⚠ Skipped session ({row['room_id']}, {row['agent_id']}): {e}")

    print(f"  ✓ Migrated {migrated} room-agent sessions")


async def reset_sequences(pg_conn):
    """Reset PostgreSQL sequences to max id + 1."""
    tables = ["agents", "rooms", "messages"]
    for table in tables:
        max_id = await pg_conn.fetchval(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
        await pg_conn.execute(f"SELECT setval('{table}_id_seq', $1, true)", max_id)
        print(f"  ✓ Reset {table}_id_seq to {max_id}")


async def verify_migration(sqlite_conn, pg_conn):
    """Verify migration by comparing counts."""
    tables = ["agents", "rooms", "messages", "room_agents", "room_agent_sessions"]

    all_match = True
    for table in tables:
        sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        pg_count = await pg_conn.fetchval(f"SELECT COUNT(*) FROM {table}")

        status = "✓" if sqlite_count == pg_count else "⚠"
        if sqlite_count != pg_count:
            all_match = False
        print(f"  {status} {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")

    if all_match:
        print("\n🎉 All data migrated successfully!")
    else:
        print("\n⚠ Some records may have been skipped (likely orphaned foreign keys)")


if __name__ == "__main__":
    asyncio.run(main())
