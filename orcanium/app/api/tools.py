"""Tools API — thin HTTP wrapper around orcanium.cli.tools_config.

All tool logic lives in ``tools_config.py`` (CLI). These endpoints delegate to
the same functions so the API and CLI are always in sync — both read/write the
same ``~/.orcanium/config.yaml`` and ``~/.orcanium/.env``.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ToolToggleRequest(BaseModel):
    platform: str = "cli"
    tools: List[str]
    agent: Optional[str] = None


class PostSetupRequest(BaseModel):
    key: str


def _get_tc():
    """Import tools_config lazily (it has heavy deps)."""
    from orcanium.cli import tools_config
    return tools_config


def _load_cfg():
    """Load config from ~/.orcanium/config.yaml via the shared CLI helper."""
    from orcanium.cli.config import load_config
    return load_config()


@router.get("/")
def list_tools(platform: str = "cli"):
    """List all configurable toolsets with enabled/disabled status.

    Returns the full ``CONFIGURABLE_TOOLSETS`` list merged with the current
    enabled/disabled state from ``config.yaml`` for the given *platform*.
    """
    try:
        tc = _get_tc()
        cfg = _load_cfg()
        enabled = set(tc._get_platform_tools(cfg, platform))
        results = []
        for key, label, desc in tc.CONFIGURABLE_TOOLSETS:
            results.append({
                "key": key,
                "name": tc.gui_toolset_label(label),
                "label": label,
                "description": desc,
                "enabled": key in enabled,
                "default_off": key in tc._DEFAULT_OFF_TOOLSETS,
            })
        return {"tools": results, "platform": platform}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable")
def enable_tools(payload: ToolToggleRequest):
    """Enable one or more toolsets for a platform."""
    try:
        tc = _get_tc()
        cfg = _load_cfg()
        tc._apply_toolset_change(cfg, payload.platform, payload.tools, "enable")
        tc._save_platform_tools(cfg, payload.platform,
                                set(tc._get_platform_tools(cfg, payload.platform)))
        from orcanium.cli.config import save_config
        save_config(cfg)
        return {"status": "ok", "enabled": payload.tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable")
def disable_tools(payload: ToolToggleRequest):
    """Disable one or more toolsets for a platform."""
    try:
        tc = _get_tc()
        cfg = _load_cfg()
        tc._apply_toolset_change(cfg, payload.platform, payload.tools, "disable")
        tc._save_platform_tools(cfg, payload.platform,
                                set(tc._get_platform_tools(cfg, payload.platform)))
        from orcanium.cli.config import save_config
        save_config(cfg)
        return {"status": "ok", "disabled": payload.tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/post-setup")
def run_post_setup(payload: PostSetupRequest):
    """Run a provider's post-setup install hook.

    Valid keys are registered in ``tools_config.run_post_setup_command``.
    """
    try:
        tc = _get_tools_config()
        from argparse import Namespace
        args = Namespace(action="post-setup", names=[payload.key], platform="cli")
        exit_code = tc.run_post_setup_command(args)
        return {"status": "ok" if exit_code == 0 else "failed", "exit_code": exit_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
