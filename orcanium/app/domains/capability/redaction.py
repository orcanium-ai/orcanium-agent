"""Redaction Service — secret masking and output sanitization.

Replaces the previous ``agent.redact`` stub with a real implementation.
Every tool result and log output passes through Redaction before reaching
the gateway, frontend, TUI, or timeline.
"""

import os
import re
from typing import List, Optional, Pattern


# Patterns for common secrets and sensitive data
_SECRET_PATTERNS: List[Pattern] = [
    # API keys
    re.compile(r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?[a-z0-9_\-]{16,}["\']?'),
    # Bearer tokens
    re.compile(r'(?i)(bearer|token|jwt)\s+[a-z0-9_\-\.]{16,}'),
    # AWS keys
    re.compile(r'AKIA[0-9A-Z]{16}'),
    # Private keys
    re.compile(r'-----BEGIN\s+(RSA|EC|DSA|PRIVATE)\s+KEY-----'),
    # GitHub tokens
    re.compile(r'(?i)(gh[opu]|ghs|ghr)_[a-z0-9]{36}'),
    # Slack tokens
    re.compile(r'(xox[baprs]-)[a-z0-9\-]{10,}'),
]

# Path patterns to mask in tool output
_SENSITIVE_PATH_PATTERNS: List[Pattern] = [
    re.compile(r'/\.ssh/'),
    re.compile(r'/\.gnupg/'),
    re.compile(r'/\.config/'),
    re.compile(r'/\.aws/'),
    re.compile(r'/\.kube/'),
]


def redact_text(text: str) -> str:
    """Mask sensitive data in a text string.

    Scans for API keys, tokens, and credentials and replaces them
    with ``[REDACTED]`` placeholders.

    Args:
        text: The text to sanitize.

    Returns:
        Sanitized text with secrets masked.
    """
    if not text:
        return text

    for pattern in _SECRET_PATTERNS:
        text = pattern.sub('[REDACTED]', text)

    return text


def redact_sensitive_text(text: str) -> str:
    """Alias for redact_text — compatibility with agent.redact API."""
    return redact_text(text)


def mask_path(path: str) -> str:
    """Mask sensitive path components in a file path string."""
    for pattern in _SENSITIVE_PATH_PATTERNS:
        path = pattern.sub(lambda m: m.group(0)[:4] + "[REDACTED]/", path)
    return path


def sanitize_tool_output(output: str) -> str:
    """Sanitize tool output before sending to the user.

    Runs redaction + path masking.

    Args:
        output: Raw tool output.

    Returns:
        Sanitized output safe for display.
    """
    if not output:
        return output
    output = redact_text(output)
    output = mask_path(output)
    return output
