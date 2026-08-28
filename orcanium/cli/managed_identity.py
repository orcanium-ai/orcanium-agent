"""Managed Gateway account state for the open-source client.

This module deliberately contains no billing or account implementation. The
private Gateway service remains the authority for every managed capability.
"""

from __future__ import annotations

from dataclasses import dataclass

from orcanium.cli.managed_gateway import (
    ManagedGatewayClientError,
    configured_managed_gateway_client,
)


@dataclass(frozen=True)
class ManagedGatewayIdentityInfo:
    logged_in: bool = False
    organization_id: str | None = None
    key_id: str | None = None
    enabled_capabilities: frozenset[str] = frozenset()
    upgrade_url: str | None = None

    @property
    def inference_credential_present(self) -> bool:
        return self.logged_in

    @property
    def tool_gateway_entitled(self) -> bool:
        return bool(self.enabled_capabilities)


def get_managed_gateway_identity(force_fresh: bool = False) -> ManagedGatewayIdentityInfo:
    """Resolve optional managed access without changing BYOK behavior."""
    del force_fresh  # Capability caching belongs to the private service/client.
    client = configured_managed_gateway_client()
    if client is None:
        return ManagedGatewayIdentityInfo()
    try:
        identity = client.identity()
        capabilities = client.capabilities()
    except ManagedGatewayClientError:
        return ManagedGatewayIdentityInfo()
    return ManagedGatewayIdentityInfo(
        logged_in=True,
        organization_id=identity.organization_id,
        key_id=identity.key_id,
        enabled_capabilities=capabilities.enabled,
        upgrade_url=capabilities.upgrade_url,
    )


def format_managed_gateway_capability_message(
    account_info: ManagedGatewayIdentityInfo | None,
    capability: str = "this managed capability",
) -> str:
    if account_info and account_info.logged_in:
        if account_info.upgrade_url:
            return f"{capability} is not enabled for this Gateway key. Manage access: {account_info.upgrade_url}"
        return f"{capability} is not enabled for this Gateway key."
    return f"{capability} requires ORCANIUM_API_KEY or a local BYOK provider."
