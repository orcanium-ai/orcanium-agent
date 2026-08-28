"""Small, dependency-light tests for the public OSS architecture boundary."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _cli_help(*args: str) -> str:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "orcanium.cli.main", *args, "--help"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_runtime_boundaries_import_without_managed_credentials():
    from orcanium.cli.managed_capabilities import get_managed_capabilities
    from orcanium.cli.managed_gateway import ManagedGatewayClient
    from orcanium.cli.managed_identity import get_managed_gateway_identity

    assert ManagedGatewayClient.__init__.__defaults__ == ("https://gateway.orcanium.com",)
    assert not get_managed_gateway_identity().logged_in
    assert not get_managed_capabilities().tool_gateway_enabled


def test_public_surfaces_use_channel_rpc_and_tui():
    channel_help = _cli_help("channel")
    update_help = _cli_help("update")
    chat_help = _cli_help("chat")

    assert "Manage messaging channels" in channel_help
    assert "--rpc" in update_help
    assert "--gateway" not in update_help
    assert "--cli" not in chat_help


def test_legacy_portal_entry_points_are_not_public():
    setup_help = _cli_help("setup")
    login_help = _cli_help("login")
    dashboard_help = _cli_help("dashboard")

    assert "--portal" not in setup_help
    assert "portal-url" not in login_help
    assert "register" not in dashboard_help
