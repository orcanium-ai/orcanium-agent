import json
import os
import urllib.request
from typing import Any, Callable, Dict


def tool_read_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path:
        return "Error: Missing path argument"
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def tool_write_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    content = args.get("content", "")
    if not path:
        return "Error: Missing path argument"
    try:
        fullpath = os.path.expanduser(path)
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        with open(fullpath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written successfully to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def tool_fetch_url(args: Dict[str, Any]) -> str:
    url = args.get("url")
    if not url:
        return "Error: Missing url argument"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")
            # Extract basic text content by stripping common HTML structures simple regex
            import re

            text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
            text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<.*?>", "", text)
            text = re.sub(r"\n\s*\n", "\n", text)
            return text[:4000]  # Return first 4k chars
    except Exception as e:
        return f"Error fetching URL: {e}"


def tool_calculator(args: Dict[str, Any]) -> str:
    expr = args.get("expression")
    if not expr:
        return "Error: Missing expression argument"
    try:
        # Safe eval using limited globals
        allowed = {"__builtins__": None, "math": __import__("math")}
        res = eval(expr, allowed)
        return str(res)
    except Exception as e:
        return f"Error calculating: {e}"


# Built-in Registry
BUILTIN_TOOLS: Dict[str, Dict[str, Any]] = {
    "read_file": {
        "description": "Read contents of a local file.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to file"}},
            "required": ["path"],
        },
        "handler": tool_read_file,
    },
    "write_file": {
        "description": "Write or overwrite content to a local file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to file"},
                "content": {"type": "string", "description": "Text content to write"},
            },
            "required": ["path", "content"],
        },
        "handler": tool_write_file,
    },
    "fetch_url": {
        "description": "Fetch text content from a web page.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "The URL to load"}},
            "required": ["url"],
        },
        "handler": tool_fetch_url,
    },
    "calculator": {
        "description": "Evaluate basic mathematical expressions.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression (e.g. '2 + 2' or 'math.sqrt(16)')",
                }
            },
            "required": ["expression"],
        },
        "handler": tool_calculator,
    },
}
