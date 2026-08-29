#!/usr/bin/env python3
"""Build the versioned release tarball for orcanium-agent.

Produces ``dist/orcanium-agent-release.tar.gz`` — a self-contained source
artifact containing the ``orcanium/`` package dir (pyproject.toml + uv.lock +
source), ``setup.sh``, ``bin/``, ``LICENSE`` and ``README.md``. ``setup.sh`` and
``orcanium update`` download this tarball from GitHub Releases, so install/update
no longer require a git checkout.

Usage:
  python scripts/build_release.py
"""
from __future__ import annotations

import re
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = DIST / "orcanium-agent-release.tar.gz"

# Top-level entries to ship in the artifact.
INCLUDE = ["orcanium", "setup.sh", "bin", "LICENSE", "README.md"]

# Paths to drop inside orcanium/ (build junk, secrets, data).
EXCLUDE_PARTS = {
    "__pycache__",
    "orcanium.egg-info",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".DS_Store",
    "data",  # runtime data; not source
    ".env",
}


def current_version() -> str:
    src = ROOT / "orcanium" / "cli" / "__init__.py"
    m = re.search(r'__version__\s*=\s*"([^"]+)"', src.read_text(encoding="utf-8"))
    if not m:
        print("ERROR: __version__ not found in orcanium/cli/__init__.py", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def _excluded(path: Path, rel_root: Path) -> bool:
    rel = path.relative_to(rel_root)
    parts = set(rel.parts)
    return bool(parts & EXCLUDE_PARTS)


def build() -> None:
    version = current_version()
    DIST.mkdir(exist_ok=True)

    with tarfile.open(OUT, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for name in INCLUDE:
            src = ROOT / name
            if not src.exists():
                print(f"WARN: missing {name} — skipping", file=sys.stderr)
                continue
            if src.is_dir():
                for p in sorted(src.rglob("*")):
                    if p.is_file() and not _excluded(p, ROOT):
                        tar.add(p, arcname=p.relative_to(ROOT), recursive=False)
            else:
                tar.add(src, arcname=name, recursive=False)

    size = OUT.stat().st_size
    print(f"Built {OUT} ({size/1024/1024:.1f} MB), version {version}")


if __name__ == "__main__":
    build()
