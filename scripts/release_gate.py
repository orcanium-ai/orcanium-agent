"""Fast, dependency-light release checks for the standalone Orcanium Agent repo."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def check_python_syntax() -> None:
    for path in (ROOT / "orcanium").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def check_imports() -> None:
    code = """
import orcanium.channel
import orcanium.rpc.entry
import orcanium.cli.managed_gateway
import orcanium.cli.managed_identity
import orcanium.cli.managed_capabilities
import orcanium.cli.status
"""
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)


def check_cli_surface() -> None:
    """Each subcommand must parse --help without error, and `update` must not
    advertise any flag whose name starts with `--gateway`.

    The previous check was `if "gateway" in result.stdout.lower()` — a single
    false-positive would have blocked CI on any help-text edit that mentioned
    the word "gateway" in a benign sentence. The new check matches a real
    CLI surface (`--gateway*` flag) instead of any incidental text.
    """
    for command in (("channel", "--help"), ("doctor", "--help"), ("update", "--help")):
        result = subprocess.run(
            [sys.executable, "-m", "orcanium.cli.main", *command],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        if command[0] != "update":
            continue
        # Look for actual flag definitions, not arbitrary text mentions.
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "--gateway" in stripped:
                raise AssertionError(
                    f"update --help still exposes a `--gateway*` flag: {stripped!r}"
                )


def main() -> int:
    check_python_syntax()
    check_imports()
    check_cli_surface()
    print("orcanium-agent release gate: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
