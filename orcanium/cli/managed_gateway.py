"""Thin client for the private Orcanium Gateway service.

The local agent remains fully usable with BYOK providers. This module only
discovers managed capabilities when a user has explicitly configured an
``ORCANIUM_API_KEY``.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import httpx


DEFAULT_MANAGED_GATEWAY_URL = "https://gateway.orcanium.com"


class ManagedGatewayClientError(RuntimeError):
    """The managed Gateway could not validate or serve the configured key."""


@dataclass(frozen=True)
class ManagedGatewayIdentity:
    organization_id: str
    key_id: str


@dataclass(frozen=True)
class ManagedGatewayCapabilities:
    enabled: frozenset[str]
    upgrade_url: str | None = None

    def allows(self, capability: str) -> bool:
        return capability in self.enabled


class ManagedGatewayClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_MANAGED_GATEWAY_URL) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @classmethod
    def from_environment(cls) -> "ManagedGatewayClient | None":
        api_key = os.getenv("ORCANIUM_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key, os.getenv("ORCANIUM_GATEWAY_URL", DEFAULT_MANAGED_GATEWAY_URL))

    def _get(self, path: str) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ManagedGatewayClientError(str(exc)) from exc
        if not isinstance(payload, dict):
            raise ManagedGatewayClientError("Gateway returned an invalid response")
        return payload

    def identity(self) -> ManagedGatewayIdentity:
        payload = self._get("/v1/me")
        organization_id = payload.get("organization_id")
        key_id = payload.get("key_id")
        if not isinstance(organization_id, str) or not isinstance(key_id, str):
            raise ManagedGatewayClientError("Gateway identity response is incomplete")
        return ManagedGatewayIdentity(organization_id=organization_id, key_id=key_id)

    def capabilities(self) -> ManagedGatewayCapabilities:
        payload = self._get("/v1/capabilities")
        raw = payload.get("capabilities", [])
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise ManagedGatewayClientError("Gateway capabilities response is invalid")
        upgrade_url = payload.get("upgrade_url")
        return ManagedGatewayCapabilities(
            enabled=frozenset(raw),
            upgrade_url=upgrade_url if isinstance(upgrade_url, str) else None,
        )


def configured_managed_gateway_client() -> ManagedGatewayClient | None:
    """Return the optional managed Gateway client without affecting BYOK mode."""
    return ManagedGatewayClient.from_environment()
