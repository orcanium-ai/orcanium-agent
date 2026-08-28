from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException
from orcanium.app.core.config import (
    CONFIG_PATH,
    get_config_file_path,
    load_system_config,
    update_system_config,
)

router = APIRouter()


@router.get("/")
def get_full_config():
    """Return the entire config.yml contents as a JSON object."""
    try:
        cfg = load_system_config()
        return cfg
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/raw")
def get_raw_config():
    """Return the raw YAML content and file path."""
    try:
        path = get_config_file_path()
        content = ""
        if CONFIG_PATH.exists():
            content = CONFIG_PATH.read_text(encoding="utf-8")
        return {"yaml": content, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/raw")
def save_raw_config(payload: Dict[str, Any] = Body(...)):
    """Save raw YAML content to the config file."""
    yaml_text = payload.get("yaml", "")
    if not yaml_text.strip():
        raise HTTPException(status_code=400, detail="YAML content is empty")
    try:
        import yaml

        parsed = yaml.safe_load(yaml_text)
        if parsed is None:
            parsed = {}
        CONFIG_PATH.write_text(yaml_text, encoding="utf-8")
        return {"status": "success", "config": parsed}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update")
def update_config(payload: Dict[str, Any] = Body(...)):
    """Update the config.yml with the provided key-value pairs (shallow merge)."""
    try:
        update_system_config(payload)
        return {"status": "success", "config": load_system_config()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reload")
def trigger_reload():
    """Reload runtime settings from .env and config.yml."""
    from orcanium.app.core.config import reload_settings

    reload_settings()
    return {"status": "success", "message": "Runtime configuration reloaded."}
