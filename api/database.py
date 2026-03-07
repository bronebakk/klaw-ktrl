"""SQLite database layer using aiosqlite."""
import aiosqlite
import logging
from datetime import datetime
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)

_db: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        settings = get_settings()
        _db = await aiosqlite.connect(settings.db_path)
        _db.row_factory = aiosqlite.Row
        await _init_schema(_db)
    return _db


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def _init_schema(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     TEXT PRIMARY KEY,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS instances (
            user_id         TEXT PRIMARY KEY,
            status          TEXT NOT NULL DEFAULT 'pending',
            container_id    TEXT,
            container_name  TEXT,
            ai_provider     TEXT,
            created_at      TEXT NOT NULL,
            started_at      TEXT,
            updated_at      TEXT NOT NULL,
            error_message   TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)
    await db.commit()
    logger.info("Database schema initialized")


# ── User helpers ──────────────────────────────────────────────────────────────

async def upsert_user(user_id: str):
    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO users (user_id, created_at, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET updated_at = excluded.updated_at""",
        (user_id, now, now)
    )
    await db.commit()


# ── Instance helpers ──────────────────────────────────────────────────────────

async def create_instance_record(user_id: str, ai_provider: str):
    db = await get_db()
    now = datetime.utcnow().isoformat()
    container_name = f"openclaw-{user_id}"
    await db.execute(
        """INSERT INTO instances (user_id, status, container_name, ai_provider, created_at, updated_at)
           VALUES (?, 'pending', ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
               status = 'pending',
               container_name = excluded.container_name,
               ai_provider = excluded.ai_provider,
               updated_at = excluded.updated_at,
               error_message = NULL""",
        (user_id, container_name, ai_provider, now, now)
    )
    await db.commit()


async def update_instance(user_id: str, **kwargs):
    db = await get_db()
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    await db.execute(f"UPDATE instances SET {fields} WHERE user_id = ?", values)
    await db.commit()


async def get_instance(user_id: str) -> Optional[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM instances WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_instances() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM instances") as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_instance_record(user_id: str):
    db = await get_db()
    await db.execute("DELETE FROM instances WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    await db.commit()
