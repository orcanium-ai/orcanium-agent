"""File Safety Service — path validation, workspace restriction, traversal prevention.

Replaces the previous ``agent.file_safety`` stub with a real implementation
that the ToolExecutor calls before any filesystem operation.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple


# Directories that are never allowed for file operations
FORBIDDEN_DIRS = frozenset({
    "/etc", "/sys", "/proc", "/dev", "/boot",
    "/var/log", "/var/run", "/var/cache",
})

# File patterns that are never allowed
FORBIDDEN_PATTERNS = frozenset({
    "/etc/", "/sys/", "/proc/", "/dev/",
    ".ssh/", ".gnupg/", ".config/",
})


def validate_path(path: str, workspace: Optional[str] = None) -> Tuple[bool, str]:
    """Validate a file path for safety.

    Args:
        path: The file path to validate.
        workspace: Optional workspace root to restrict access to.

    Returns:
        (is_safe: bool, reason: str)
    """
    try:
        resolved = Path(path).resolve()
    except Exception as e:
        return False, f"Cannot resolve path: {e}"

    # Reject forbidden directories
    for forbidden in FORBIDDEN_DIRS:
        if str(resolved).startswith(forbidden):
            return False, f"Path resolves to forbidden directory: {forbidden}"

    # Reject forbidden patterns
    str_path = str(resolved).lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in str_path:
            return False, f"Path contains forbidden pattern: {pattern}"

    # Workspace restriction
    if workspace:
        try:
            ws = Path(workspace).resolve()
            if not str(resolved).startswith(str(ws)):
                return False, f"Path is outside the workspace: {workspace}"
        except Exception:
            return False, "Invalid workspace path"

    # Symlink validation
    if resolved.is_symlink():
        target = resolved.resolve()
        if workspace and not str(target).startswith(str(Path(workspace).resolve())):
            return False, "Symlink target is outside the workspace"

    return True, ""


def is_forbidden_path(path: str) -> bool:
    """Quick check if a path should be rejected."""
    safe, _ = validate_path(path)
    return not safe


def get_read_block_error(path: str, workspace: Optional[str] = None) -> Optional[str]:
    """Return an error message if the path cannot be read, or None if safe."""
    safe, reason = validate_path(path, workspace)
    if not safe:
        return reason
    try:
        p = Path(path)
        if not p.exists():
            return f"File not found: {path}"
        if not p.is_file():
            return f"Not a file: {path}"
    except Exception as e:
        return str(e)
    return None
