"""API endpoints for authentication (setup, login, logout, status)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from orcanium.app.core.auth import (
    get_current_user,
    is_auth_enabled,
    is_setup_complete,
    load_persisted_tokens,
    login,
    logout,
    setup_admin,
)
from orcanium.app.core.db import engine, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────


class SetupRequest(BaseModel):
    password: str


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthStatusResponse(BaseModel):
    setup_complete: bool
    authenticated: bool
    user: str | None = None


# ── Middleware: optionally protect all /api/v1/ routes ─────────────────────


async def auth_guard(request: Request):
    """Optional middleware dependency — protects routes when auth is enabled."""
    if not is_auth_enabled():
        return {"username": "dev", "auth_disabled": True}
    return await get_current_user(request)


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/auth/setup", response_model=AuthStatusResponse)
def check_setup_status():
    """Check whether admin password has been configured."""
    return AuthStatusResponse(
        setup_complete=is_setup_complete(engine),
        authenticated=False,
    )


@router.post("/auth/setup", response_model=TokenResponse)
def perform_setup(body: SetupRequest):
    """Configure the admin password (first run only)."""
    if len(body.password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 4 characters.",
        )
    token = setup_admin(engine, body.password)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def perform_login(body: LoginRequest):
    """Authenticate with the admin password."""
    token = login(engine, body.password)
    return TokenResponse(access_token=token)


@router.post("/auth/logout")
def perform_logout(request: Request):
    """Invalidate the current session token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        logout(engine, token)
    return {"status": "logged_out"}


@router.get("/auth/status")
def auth_status(request: Request):
    """Return current authentication status."""
    if not is_auth_enabled():
        return AuthStatusResponse(setup_complete=True, authenticated=True, user="dev")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return AuthStatusResponse(
            setup_complete=is_setup_complete(engine), authenticated=False
        )

    from orcanium.app.core.auth import validate_token

    info = validate_token(engine, auth_header[7:])
    if info:
        return AuthStatusResponse(
            setup_complete=True, authenticated=True, user=info.get("username", "admin")
        )
    return AuthStatusResponse(
        setup_complete=is_setup_complete(engine), authenticated=False
    )


@router.get("/auth/check")
def check_auth(user: dict = Depends(auth_guard)):
    """Simple check endpoint — returns 200 if authenticated, 401 otherwise."""
    return {"authenticated": True, "user": user}
