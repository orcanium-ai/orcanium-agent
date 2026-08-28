"""Built-in tool handlers registered with ToolRegistry.

Uses the reference-agent's registry API (positional args + named params).
"""

import json
import os
import urllib.request
from typing import Any, Dict

from orcanium.app.tools.registry import registry

# ── Handlers ────────────────────────────────────────────────────


def _handle_read_file(args: Dict[str, Any], **kwargs) -> str:
    path = args.get("path")
    if not path:
        return json.dumps({"error": "Missing path argument"})
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return json.dumps({"error": f"Error reading file: {e}"})


def _handle_write_file(args: Dict[str, Any], **kwargs) -> str:
    path = args.get("path")
    content = args.get("content", "")
    if not path:
        return json.dumps({"error": "Missing path argument"})
    try:
        fullpath = os.path.expanduser(path)
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        with open(fullpath, "w", encoding="utf-8") as f:
            f.write(content)
        return json.dumps({"status": "ok", "message": f"File written to {path}"})
    except Exception as e:
        return json.dumps({"error": f"Error writing file: {e}"})


def _handle_fetch_url(args: Dict[str, Any], **kwargs) -> str:
    url = args.get("url")
    if not url:
        return json.dumps({"error": "Missing url argument"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")
        import re
        text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<.*?>", "", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        return text[:4000]
    except Exception as e:
        return json.dumps({"error": f"Error fetching URL: {e}"})


def _handle_calculator(args: Dict[str, Any], **kwargs) -> str:
    expr = args.get("expression")
    if not expr:
        return json.dumps({"error": "Missing expression argument"})
    try:
        allowed = {"__builtins__": {}, "math": __import__("math")}
        result = eval(expr, allowed)
        return str(result)
    except Exception as e:
        return json.dumps({"error": f"Error calculating: {e}"})


# ── Registration (reference-agent registry API) ──────────────────

def register_builtin_tools():
    """Register all built-in tools with the ToolRegistry."""

    registry.register(
        "read_file", "core",
        {
            "description": "Read contents of a local file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to the file to read"}},
                "required": ["path"],
            },
        },
        _handle_read_file,
        emoji="📄",
    )

    registry.register(
        "write_file", "core",
        {
            "description": "Write or overwrite content to a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Text content to write"},
                },
                "required": ["path", "content"],
            },
        },
        _handle_write_file,
        emoji="✏️",
    )

    registry.register(
        "fetch_url", "core",
        {
            "description": "Fetch text content from a web page.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL to fetch"}},
                "required": ["url"],
            },
        },
        _handle_fetch_url,
        emoji="🌐",
    )

    registry.register(
        "calculator", "core",
        {
            "description": "Evaluate basic mathematical expressions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression (e.g. '2 + 2')"}
                },
                "required": ["expression"],
            },
        },
        _handle_calculator,
        emoji="🔢",
    )


# Auto-register on import
register_builtin_tools()
