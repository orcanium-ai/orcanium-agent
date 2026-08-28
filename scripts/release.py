#!/usr/bin/env python3
"""Bump version in lockstep across all sources.

Usage:
  python scripts/release.py patch        # 0.1.0 → 0.1.1
  python scripts/release.py minor        # 0.1.0 → 0.2.0
  python scripts/release.py major        # 0.1.0 → 1.0.0
  python scripts/release.py 0.2.0        # explicit version string
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS: dict[str, re.Pattern] = {
    "cli/__init__.py": re.compile(r'__version__\s*=\s*"([^"]+)"'),
    "pyproject.toml": re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE),
}

FILES = (
    ROOT / "orcanium" / "cli" / "__init__.py",
    ROOT / "orcanium" / "pyproject.toml",
)


def _current_version() -> str:
    src = FILES[0]
    m = PATTERNS["cli/__init__.py"].search(src.read_text(encoding="utf-8"))
    if not m:
        print("ERROR: version pattern not found in cli/__init__.py", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def _bump_semver(current: str, part: str) -> str:
    major, minor, patch = (int(x) for x in current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    return part  # raw version string


def _write_version(new_version: str) -> None:
    for path in FILES:
        key = "cli/__init__.py" if "cli" in path.parts else "pyproject.toml"
        pat = PATTERNS[key]
        text = path.read_text(encoding="utf-8")
        m = pat.search(text)
        if not m:
            print(f"  WARN: pattern not found in {path.name}")
            continue
        old = m.group(1)
        if "__version__" in m.group():
            text = pat.sub(f'__version__ = "{new_version}"', text)
        else:
            text = pat.sub(f'version = "{new_version}"', text)
        path.write_text(text, encoding="utf-8")
        print(f"  {path.relative_to(ROOT)}: {old} → {new_version}")


def main() -> None:
    current = _current_version()
    arg = sys.argv[1] if len(sys.argv) > 1 else "patch"
    new = _bump_semver(current, arg)
    print(f"  {current} → {new}")
    _write_version(new)


if __name__ == "__main__":
    main()
