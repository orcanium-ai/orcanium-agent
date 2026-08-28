"""FTS5 full-text search for sessions and messages.

Provides search functions that query SQLite FTS5 virtual tables
to find sessions and messages matching a search query.
"""

import logging
import re
from typing import List, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from orcanium.app.core.db import Message, SessionLocal
from orcanium.app.core.db import Session as DbSession

logger = logging.getLogger(__name__)

# ── FTS5 table names ───────────────────────────────────────

FTS_MESSAGES_TABLE = "messages_fts"
FTS_SESSIONS_TABLE = "sessions_fts"


def ensure_fts_tables(engine):
    """Create FTS5 virtual tables and triggers if they don't exist.

    Must be called after init_db() / during migration.
    FTS tables use a separate TEXT column for the source row ID
    instead of relying on rowid (which requires INTEGER).
    """
    with engine.connect() as conn:
        # Drop old triggers that incorrectly used rowid=new.id (string)
        for trig in [
            "messages_fts_insert",
            "messages_fts_delete",
            "messages_fts_update",
        ]:
            conn.execute(sa_text(f"DROP TRIGGER IF EXISTS {trig}"))

        # Drop and recreate FTS table with id as a proper column
        conn.execute(sa_text(f"DROP TABLE IF EXISTS {FTS_MESSAGES_TABLE}"))
        conn.execute(
            sa_text(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_MESSAGES_TABLE} "
                "USING fts5(id UNINDEXED, content, session_id UNINDEXED, "
                "tokenize='porter unicode61')"
            )
        )

        # Sessions FTS — search session titles
        conn.execute(
            sa_text(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_SESSIONS_TABLE} "
                "USING fts5(title, agent_name UNINDEXED, tokenize='porter unicode61')"
            )
        )

        # Triggers to keep FTS in sync with new messages
        # NOTE: Only INSERT trigger is used. DELETE/UPDATE triggers are
        # omitted because the FTS5 'delete' command requires rowid (integer)
        # while our FTS table uses a TEXT id column. Stale FTS entries are
        # harmless — rebuild via index_existing_messages() if needed.
        _create_fts_trigger(
            conn,
            "messages_fts_insert",
            "AFTER INSERT ON messages",
            f"INSERT INTO {FTS_MESSAGES_TABLE}(id, content, session_id) "
            "VALUES (new.id, new.content, new.session_id)",
        )

        conn.commit()


def _create_fts_trigger(conn, trigger_name: str, event: str, sql: str):
    """Create a trigger if it doesn't already exist."""
    conn.execute(
        sa_text(f"CREATE TRIGGER IF NOT EXISTS {trigger_name} {event} BEGIN {sql}; END")
    )


def rebuild_fts_indexes(engine):
    """Rebuild FTS indexes from scratch — useful after bulk imports."""
    with engine.connect() as conn:
        for table in [FTS_MESSAGES_TABLE, FTS_SESSIONS_TABLE]:
            try:
                conn.execute(sa_text(f"INSERT INTO {table}({table}) VALUES('rebuild')"))
            except Exception as e:
                logger.warning(f"FTS rebuild failed for {table}: {e}")
        conn.commit()


def search_messages(
    db: Session,
    query: str,
    agent_name: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """Search messages by content using FTS5.

    Returns list of {session_id, content, sender, timestamp, rank}.
    """
    if not query.strip():
        return []

    # Sanitize the query for FTS5 (remove special chars, keep alphanumeric)
    safe_query = _sanitize_fts_query(query)

    sql = (
        f"SELECT m.id, m.session_id, m.content, m.sender, m.timestamp, "
        f"  rank "
        f"FROM {FTS_MESSAGES_TABLE} f "
        f"JOIN messages m ON m.id = f.id "
        f"WHERE {FTS_MESSAGES_TABLE} MATCH :q "
    )
    params = {"q": safe_query}

    if agent_name:
        sql += (
            " AND m.session_id IN (SELECT id FROM sessions WHERE agent_name = :agent)"
        )
        params["agent_name"] = agent_name

    sql += " ORDER BY rank LIMIT :lim"
    params["lim"] = limit

    try:
        rows = db.execute(sa_text(sql), params).fetchall()
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "content": r[2],
                "sender": r[3],
                "timestamp": str(r[4]) if r[4] else None,
                "rank": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"FTS5 search failed: {e}")
        return []


def search_sessions(
    db: Session,
    query: str,
    agent_name: Optional[str] = None,
    limit: int = 20,
) -> List[dict]:
    """Search sessions by title using FTS5.

    Returns list of {id, agent_name, title, created_at, updated_at, rank}.
    """
    if not query.strip():
        return []

    safe_query = _sanitize_fts_query(query)

    sql = (
        f"SELECT s.id, s.agent_name, s.title, s.created_at, s.updated_at, "
        f"  rank "
        f"FROM {FTS_SESSIONS_TABLE} f "
        f"JOIN sessions s ON s.id = f.rowid "
        f"WHERE {FTS_SESSIONS_TABLE} MATCH :q "
    )
    params = {"q": safe_query}

    if agent_name:
        sql += " AND s.agent_name = :agent"
        params["agent_name"] = agent_name

    sql += " ORDER BY rank LIMIT :lim"
    params["lim"] = limit

    try:
        rows = db.execute(sa_text(sql), params).fetchall()
        return [
            {
                "id": r[0],
                "agent_name": r[1],
                "title": r[2],
                "created_at": str(r[3]) if r[3] else None,
                "updated_at": str(r[4]) if r[4] else None,
                "rank": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"FTS5 session search failed: {e}")
        return []


def _sanitize_fts_query(query: str) -> str:
    """Clean user input for safe FTS5 querying.

    Removes special characters, trims, and escapes quotes.
    """
    # Remove FTS5 special characters but keep alphanumeric and spaces
    cleaned = re.sub(r'[^\w\s"\-]', " ", query)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""

    # Wrap in double quotes for phrase matching to avoid FTS5 syntax errors
    # But if it's already quoted, leave it
    if not cleaned.startswith('"'):
        cleaned = f'"{cleaned}"'

    return cleaned


def index_existing_messages(engine):
    """Bulk-index all existing messages into FTS tables.

    Call this once during migration to backfill the FTS index.
    """
    db = SessionLocal()
    try:
        messages = db.query(Message).all()
        with engine.connect() as conn:
            for msg in messages:
                try:
                    conn.execute(
                        sa_text(
                            f"INSERT OR IGNORE INTO {FTS_MESSAGES_TABLE} "
                            "(id, content, session_id) VALUES (:id, :content, :sid)"
                        ),
                        {"id": msg.id, "content": msg.content, "sid": msg.session_id},
                    )
                except Exception:
                    pass

            sessions = db.query(DbSession).all()
            for sess in sessions:
                try:
                    conn.execute(
                        sa_text(
                            f"INSERT OR IGNORE INTO {FTS_SESSIONS_TABLE} "
                            "(rowid, title, agent_name) VALUES (:id, :title, :agent)"
                        ),
                        {
                            "id": sess.id,
                            "title": sess.title or "",
                            "agent": sess.agent_name,
                        },
                    )
                except Exception:
                    pass
            conn.commit()
    finally:
        db.close()
