"""Authentication module for Orcanium.

Minimal single-user authentication using bcrypt password hashing
and session tokens stored in the SQLite _meta table.

Provides:
- Admin password setup (first-run flow)
- Password-based login
- Token-based session validation
- A FastAPI middleware / dependency for protecting routes
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text as sa_text
from sqlalchemy.engine import Engine

from orcanium.app.core.config import settings

logger = logging.getLogger(__name__)

# Keys used in the _meta table
META_KEY_PASSWORD_HASH = "auth_admin_password_hash"
META_KEY_SALT = "auth_salt"

# In-memory token store: {token_sha256: {username, expires_at, created_at}}
# Tokens are also stored in _meta for persistence across restarts.
_active_tokens: dict[str, dict] = {}
TOKEN_TTL_S = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


# ── Password Hashing (SHA-256 HMAC with salt, no bcrypt dependency) ───────


def _generate_salt() -> str:
    return secrets.token_hex(32)


def _hash_password(password: str, salt: str) -> str:
    """Return HMAC-SHA256 hex digest of password with given salt."""
    return hmac.new(
        salt.encode("utf-8"), password.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return hmac.compare_digest(_hash_password(password, salt), stored_hash)


# ── Meta table helpers ────────────────────────────────────────────────────


def _get_meta(engine: Engine, key: str) -> Optional[str]:
    with engine.connect() as conn:
        row = conn.execute(
            sa_text("SELECT value FROM _meta WHERE key = :k"), {"k": key}
        ).fetchone()
        return row[0] if row else None


def _set_meta(engine: Engine, key: str, value: str):
    with engine.connect() as conn:
        existing = conn.execute(
            sa_text("SELECT value FROM _meta WHERE key = :k"), {"k": key}
        ).fetchone()
        if existing:
            conn.execute(
                sa_text("UPDATE _meta SET value = :v WHERE key = :k"),
                {"v": value, "k": key},
            )
        else:
            conn.execute(
                sa_text("INSERT INTO _meta (key, value) VALUES (:k, :v)"),
                {"k": key, "v": value},
            )
        conn.commit()


def _delete_meta(engine: Engine, key: str):
    with engine.connect() as conn:
        conn.execute(sa_text("DELETE FROM _meta WHERE key = :k"), {"k": key})
        conn.commit()


# ── Public Auth API ───────────────────────────────────────────────────────


def is_setup_complete(engine: Engine) -> bool:
    """Return True if the admin password has been configured."""
    return _get_meta(engine, META_KEY_PASSWORD_HASH) is not None


def setup_admin(engine: Engine, password: str) -> str:
    """Set the admin password (first-run setup).

    Raises HTTPException(409) if already configured.
    Returns a login token.
    """
    if is_setup_complete(engine):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin password already configured.",
        )
    salt = _generate_salt()
    pw_hash = _hash_password(password, salt)
    _set_meta(engine, META_KEY_PASSWORD_HASH, pw_hash)
    _set_meta(engine, META_KEY_SALT, salt)
    logger.info("Admin password configured.")
    return _create_token(engine, "admin")


def login(engine: Engine, password: str) -> str:
    """Authenticate with the admin password.

    Returns a session token string on success.
    Raises HTTPException(401) on failure.
    """
    stored_hash = _get_meta(engine, META_KEY_PASSWORD_HASH)
    salt = _get_meta(engine, META_KEY_SALT)
    if not stored_hash or not salt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not configured. Please complete setup first.",
        )
    if not _verify_password(password, salt, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )
    return _create_token(engine, "admin")


def logout(engine: Engine, token: str):
    """Invalidate a session token."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    _active_tokens.pop(token_hash, None)
    # Remove from persistent store
    stored = _get_meta(engine, f"auth_token_{token_hash}")
    if stored:
        _delete_meta(engine, f"auth_token_{token_hash}")


def validate_token(engine: Engine, token: str) -> Optional[dict]:
    """Validate a token. Returns token info dict or None."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    # Check in-memory first
    info = _active_tokens.get(token_hash)
    if info:
        if info["expires_at"] > time.time():
            return info
        _active_tokens.pop(token_hash, None)
        return None
    # Fallback to persistent store (after restart)
    stored = _get_meta(engine, f"auth_token_{token_hash}")
    if stored:
        try:
            parts = stored.split("|")
            info = {
                "username": parts[0],
                "expires_at": float(parts[1]),
                "created_at": parts[2],
            }
            if info["expires_at"] > time.time():
                _active_tokens[token_hash] = info
                return info
            _delete_meta(engine, f"auth_token_{token_hash}")
        except (IndexError, ValueError):
            _delete_meta(engine, f"auth_token_{token_hash}")
    return None


def _create_token(engine: Engine, username: str) -> str:
    """Generate and store a new session token."""
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = time.time() + TOKEN_TTL_S
    info = {
        "username": username,
        "expires_at": expires_at,
        "created_at": str(time.time()),
    }
    _active_tokens[token_hash] = info
    # Persist to _meta so tokens survive restart
    _set_meta(engine, f"auth_token_{token_hash}", f"{username}|{expires_at}|{info['created_at']}")
    return token


# ── FastAPI Middleware / Dependency ───────────────────────────────────────


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency that validates the Bearer token.

    Usage:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            ...
    """
    # Import here to avoid circular import at module level
    from orcanium.app.core.db import engine

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[7:]
    info = validate_token(engine, token)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return info


def is_auth_enabled() -> bool:
    """Return True if authentication is enforced.

    Auth is enabled by default.  Set DISABLE_AUTH=1 in ~/.orcanium/.env
    to disable (useful during development).
    """
    return os.environ.get("DISABLE_AUTH", "").strip() not in ("1", "true", "yes")


# ── Startup: load persisted tokens into memory ────────────────────────────

def load_persisted_tokens(engine: Engine):
    """On startup, load any non-expired tokens from _meta into memory."""
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text("SELECT key, value FROM _meta WHERE key LIKE 'auth_token_%'")
        ).fetchall()
    now = time.time()
    loaded = 0
    for key, value in rows:
        try:
            parts = value.split("|")
            expires_at = float(parts[1])
            if expires_at > now:
                token_hash = key.replace("auth_token_", "", 1)
                _active_tokens[token_hash] = {
                    "username": parts[0],
                    "expires_at": expires_at,
                    "created_at": parts[2],
                }
                loaded += 1
            else:
                _delete_meta(engine, key)
        except (IndexError, ValueError):
            _delete_meta(engine, key)
    if loaded:
        logger.info(f"Loaded {loaded} persisted auth tokens.")
