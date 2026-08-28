"""Generic managed-tool gateway helpers for Orcanium-hosted vendor passthroughs."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

from orcanium.channel.compat import get_orcanium_home
from orcanium.app.tools.tool_backend_helpers import managed_orcanium_tools_enabled

_DEFAULT_TOOL_GATEWAY_DOMAIN = "orcanium.com"
_DEFAULT_TOOL_GATEWAY_SCHEME = "https"
_ORCANIUM_ACCESS_TOKEN_REFRESH_SKEW_SECONDS = 120


@dataclass(frozen=True)
class ManagedToolGatewayConfig:
    vendor: str
    gateway_origin: str
    orcanium_user_token: str
    managed_mode: bool


def auth_json_path():
    """Return the Orcanium auth store path, respecting ORCANIUM_HOME overrides."""
    return get_orcanium_home() / "auth.json"


def _read_orcanium_provider_state() -> Optional[dict]:
    try:
        path = auth_json_path()
        if not path.is_file():
            return None
        data = json.loads(path.read_text())
        providers = data.get("providers", {})
        if not isinstance(providers, dict):
            return None
        orcanium_provider = providers.get("orcanium", {})
        if isinstance(orcanium_provider, dict):
            return orcanium_provider
    except Exception:
        pass
    return None


def _parse_timestamp(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _access_token_is_expiring(expires_at: object, skew_seconds: int) -> bool:
    expires = _parse_timestamp(expires_at)
    if expires is None:
        return True
    remaining = (expires - datetime.now(timezone.utc)).total_seconds()
    return remaining <= max(0, int(skew_seconds))


def peek_orcanium_access_token() -> Optional[str]:
    """Cheap probe for a Orcanium gateway token without triggering refresh.

    Availability scans (`orcanium tools`, banner/status paint, provider
    `is_available()` checks) must stay off the synchroorcanium OAuth refresh path.
    This helper therefore only inspects the explicit env override and the
    cached auth-store token, without checking expiry and without making any
    network calls. Truthful refresh handling stays in request/session paths
    that call :func:`read_orcanium_access_token`.
    """
    explicit = os.getenv("TOOL_GATEWAY_USER_TOKEN")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    orcanium_provider = _read_orcanium_provider_state() or {}
    access_token = orcanium_provider.get("access_token")
    if isinstance(access_token, str) and access_token.strip():
        return access_token.strip()
    return None


def read_orcanium_access_token() -> Optional[str]:
    """Read a Orcanium Subscriber OAuth access token from auth store or env override."""
    explicit = os.getenv("TOOL_GATEWAY_USER_TOKEN")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    orcanium_provider = _read_orcanium_provider_state() or {}
    cached_token = peek_orcanium_access_token()

    if cached_token and not _access_token_is_expiring(
        orcanium_provider.get("expires_at"),
        _ORCANIUM_ACCESS_TOKEN_REFRESH_SKEW_SECONDS,
    ):
        return cached_token

    try:
        from orcanium.cli.auth import resolve_orcanium_access_token

        refreshed_token = resolve_orcanium_access_token(
            refresh_skew_seconds=_ORCANIUM_ACCESS_TOKEN_REFRESH_SKEW_SECONDS,
        )
        if isinstance(refreshed_token, str) and refreshed_token.strip():
            return refreshed_token.strip()
    except Exception as exc:
        logger.debug("Orcanium access token refresh failed: %s", exc)

    return cached_token


def get_tool_gateway_scheme() -> str:
    """Return configured shared gateway URL scheme."""
    scheme = os.getenv("TOOL_GATEWAY_SCHEME", "").strip().lower()
    if not scheme:
        return _DEFAULT_TOOL_GATEWAY_SCHEME

    if scheme in {"http", "https"}:
        return scheme

    raise ValueError("TOOL_GATEWAY_SCHEME must be 'http' or 'https'")


def build_vendor_gateway_url(vendor: str) -> str:
    """Return the gateway origin for a specific vendor."""
    vendor_key = f"{vendor.upper().replace('-', '_')}_GATEWAY_URL"
    explicit_vendor_url = os.getenv(vendor_key, "").strip().rstrip("/")
    if explicit_vendor_url:
        return explicit_vendor_url

    shared_scheme = get_tool_gateway_scheme()
    shared_domain = os.getenv("TOOL_GATEWAY_DOMAIN", "").strip().strip("/")
    if shared_domain:
        return f"{shared_scheme}://{vendor}-channel.{shared_domain}"

    return f"{shared_scheme}://{vendor}-channel.{_DEFAULT_TOOL_GATEWAY_DOMAIN}"


def resolve_managed_tool_gateway(
    vendor: str,
    gateway_builder: Optional[Callable[[str], str]] = None,
    token_reader: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[ManagedToolGatewayConfig]:
    """Resolve shared managed-tool gateway config for a vendor."""
    if not managed_orcanium_tools_enabled():
        return None

    resolved_gateway_builder = gateway_builder or build_vendor_gateway_url
    resolved_token_reader = token_reader or read_orcanium_access_token

    gateway_origin = resolved_gateway_builder(vendor)
    orcanium_user_token = resolved_token_reader()
    if not gateway_origin or not orcanium_user_token:
        return None

    return ManagedToolGatewayConfig(
        vendor=vendor,
        gateway_origin=gateway_origin,
        orcanium_user_token=orcanium_user_token,
        managed_mode=True,
    )


def is_managed_tool_gateway_ready(
    vendor: str,
    gateway_builder: Optional[Callable[[str], str]] = None,
    token_reader: Optional[Callable[[], Optional[str]]] = None,
) -> bool:
    """Return True when gateway URL and a likely-usable Orcanium token are present.

    Defaults to :func:`peek_orcanium_access_token` so read-only availability scans
    avoid synchroorcanium OAuth refresh. Callers that are about to make a real
    gateway request should use :func:`resolve_managed_tool_gateway` (which
    still defaults to the refresh-aware :func:`read_orcanium_access_token`).
    """
    return resolve_managed_tool_gateway(
        vendor,
        gateway_builder=gateway_builder,
        token_reader=token_reader or peek_orcanium_access_token,
    ) is not None
