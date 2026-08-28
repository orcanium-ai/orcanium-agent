"""Schema migration support for Orcanium SQLite database.

Migrations are versioned functions stored in a ``_MIGRATIONS`` list.
Each migration has a version number and a callable that performs the
schema change.  On startup, ``run_pending_migrations()`` checks the
current schema version stored in ``_meta`` table and runs any
outstanding migrations in order.

Usage:
    from orcanium.app.core.migrations import run_pending_migrations, get_schema_version

    # At startup, after init_db():
    run_pending_migrations(engine)
"""

import logging
from typing import List, Tuple

from sqlalchemy import text as sa_text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Schema version stored in the _meta table
META_TABLE = "_meta"
VERSION_KEY = "schema_version"

# Each migration is (version_number, description, callable(engine))
Migration = Tuple[int, str, callable]

_MIGRATIONS: List[Migration] = []


def _ensure_meta_table(engine: Engine):
    """Create the _meta table if it doesn't exist."""
    with engine.connect() as conn:
        conn.execute(
            sa_text(
                f"CREATE TABLE IF NOT EXISTS {META_TABLE} ("
                "  key TEXT PRIMARY KEY,"
                "  value TEXT NOT NULL"
                ")"
            )
        )
        conn.commit()


def get_schema_version(engine: Engine) -> int:
    """Return the current schema version, or 0 if not set."""
    _ensure_meta_table(engine)
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(f"SELECT value FROM {META_TABLE} WHERE key = :k"),
            {"k": VERSION_KEY},
        ).fetchone()
        if row:
            return int(row[0])
    return 0


def _set_schema_version(engine: Engine, version: int):
    with engine.connect() as conn:
        # UPSERT pattern
        existing = conn.execute(
            sa_text(f"SELECT value FROM {META_TABLE} WHERE key = :k"),
            {"k": VERSION_KEY},
        ).fetchone()
        if existing:
            conn.execute(
                sa_text(f"UPDATE {META_TABLE} SET value = :v WHERE key = :k"),
                {"v": str(version), "k": VERSION_KEY},
            )
        else:
            conn.execute(
                sa_text(f"INSERT INTO {META_TABLE} (key, value) VALUES (:k, :v)"),
                {"k": VERSION_KEY, "v": str(version)},
            )
        conn.commit()


def migration(version: int, description: str):
    """Decorator to register a migration function."""

    def decorator(func: callable):
        _MIGRATIONS.append((version, description, func))
        _MIGRATIONS.sort(key=lambda m: m[0])  # keep sorted
        return func

    return decorator


def run_pending_migrations(engine: Engine):
    """Run all migrations with version > current schema version."""
    current = get_schema_version(engine)
    latest = max((m[0] for m in _MIGRATIONS), default=0)

    if current >= latest:
        logger.info(f"Schema at version {current} (latest). No migrations needed.")
        return

    for version, description, func in _MIGRATIONS:
        if version > current:
            logger.info(f"Running migration v{version}: {description}")
            try:
                func(engine)
                _set_schema_version(engine, version)
                logger.info(f"Migration v{version} complete.")
            except Exception as e:
                logger.error(f"Migration v{version} failed: {e}")
                raise

    logger.info(f"Schema upgraded from v{current} to v{latest}.")


# ── Migrations ──────────────────────────────────────────────


@migration(1, "Add archived_at column to sessions table")
def _migration_001(engine: Engine):
    with engine.connect() as conn:
        # SQLite doesn't support ADD COLUMN IF NOT EXISTS, so catch error
        try:
            conn.execute(
                sa_text("ALTER TABLE sessions ADD COLUMN archived_at DATETIME")
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.info("Column archived_at already exists on sessions.")


@migration(2, "Add total_input_tokens and total_output_tokens to sessions")
def _migration_002(engine: Engine):
    with engine.connect() as conn:
        for col in ["total_input_tokens", "total_output_tokens"]:
            try:
                conn.execute(
                    sa_text(f"ALTER TABLE sessions ADD COLUMN {col} INTEGER DEFAULT 0")
                )
                conn.commit()
            except Exception:
                conn.rollback()
                logger.info(f"Column {col} already exists on sessions.")


@migration(3, "Add source column to sessions")
def _migration_003(engine: Engine):
    with engine.connect() as conn:
        try:
            conn.execute(
                sa_text("ALTER TABLE sessions ADD COLUMN source TEXT DEFAULT 'api'")
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.info("Column source already exists on sessions.")


@migration(4, "Create agent_runtime_state table")
def _migration_004(engine: Engine):
    with engine.connect() as conn:
        conn.execute(
            sa_text("""
                CREATE TABLE IF NOT EXISTS agent_runtime_state (
                    agent_id TEXT PRIMARY KEY,
                    turns_since_memory INTEGER NOT NULL DEFAULT 0,
                    turns_since_skill INTEGER NOT NULL DEFAULT 0,
                    last_memory_review TIMESTAMP NULL,
                    last_skill_review TIMESTAMP NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
        )
        conn.commit()


@migration(5, "Add turns_since_user column to agent_runtime_state")
def _migration_005(engine: Engine):
    with engine.connect() as conn:
        try:
            conn.execute(
                sa_text(
                    "ALTER TABLE agent_runtime_state ADD COLUMN turns_since_user INTEGER NOT NULL DEFAULT 0"
                )
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.info(
                "Column turns_since_user already exists on agent_runtime_state."
            )

    with engine.connect() as conn:
        try:
            conn.execute(
                sa_text(
                    "ALTER TABLE agent_runtime_state ADD COLUMN last_user_review TIMESTAMP NULL"
                )
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.info(
                "Column last_user_review already exists on agent_runtime_state."
            )


@migration(6, "Add workflow_id and parent_event_id to timeline_events")
def _migration_006(engine: Engine):
    with engine.connect() as conn:
        for col in ["workflow_id", "parent_event_id"]:
            try:
                conn.execute(
                    sa_text(f"ALTER TABLE timeline_events ADD COLUMN {col} TEXT NULL")
                )
                conn.commit()
            except Exception:
                conn.rollback()
                logger.info(f"Column {col} already exists on timeline_events.")


@migration(7, "Rename gateway_channels table to channel_configs")
def _migration_007(engine: Engine):
    with engine.connect() as conn:
        try:
            conn.execute(sa_text("ALTER TABLE gateway_channels RENAME TO channel_configs"))
            conn.commit()
            logger.info("Renamed gateway_channels → channel_configs.")
        except Exception:
            conn.rollback()
            logger.info("Table gateway_channels already renamed or does not exist.")


@migration(8, "Create cross-talk requests table")
def _migration_008(engine: Engine):
    # Keep this SQL migration independent of ORM metadata so it works against
    # databases created by older releases.
    with engine.connect() as conn:
        conn.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS cross_talk_requests (
                id TEXT PRIMARY KEY,
                source_agent_id TEXT NOT NULL,
                target_agent_id TEXT NOT NULL,
                source_session_id TEXT NULL,
                target_session_id TEXT NULL,
                turn_id TEXT NULL,
                request_text TEXT NOT NULL,
                context_summary TEXT NULL,
                status TEXT NOT NULL DEFAULT 'pending_permission',
                result TEXT NULL,
                error TEXT NULL,
                hop INTEGER NOT NULL DEFAULT 0,
                expires_at TIMESTAMP NULL,
                created_at TIMESTAMP NULL,
                updated_at TIMESTAMP NULL
            )
        """))
        conn.execute(sa_text("CREATE INDEX IF NOT EXISTS ix_cross_talk_status ON cross_talk_requests(status)"))
        conn.execute(sa_text("CREATE INDEX IF NOT EXISTS ix_cross_talk_source ON cross_talk_requests(source_agent_id)"))
        conn.execute(sa_text("CREATE INDEX IF NOT EXISTS ix_cross_talk_target ON cross_talk_requests(target_agent_id)"))
        conn.execute(sa_text("CREATE INDEX IF NOT EXISTS ix_cross_talk_turn ON cross_talk_requests(turn_id)"))
        conn.commit()
