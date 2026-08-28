import datetime
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from orcanium.app.core.config import (
    load_env_keys,
    reload_settings,
    save_env_keys,
    settings,
)
from orcanium.app.core.db import ProviderMetadata, get_db
from orcanium.app.model.model_gateway import ModelGateway

router = APIRouter()

# Default predefined providers list for V1
PREDEFINED_PROVIDERS = {
    # API key based providers
    "openai": {"name": "OpenAI", "env_var": "OPENAI_API_KEY", "type": "provider"},
    "anthropic": {
        "name": "Anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "type": "provider",
    },
    "gemini": {
        "name": "Gemini",
        "env_var": "GEMINI_API_KEY",
        "type": "provider",
    },
    "google": {
        "name": "Gemini",
        "env_var": "GOOGLE_API_KEY",
        "type": "provider",
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_var": "OPENROUTER_API_KEY",
        "type": "provider",
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_var": "DEEPSEEK_API_KEY",
        "type": "provider",
    },
    "groq": {"name": "Groq Cloud", "env_var": "GROQ_API_KEY", "type": "provider"},
    "together": {
        "name": "Together AI",
        "env_var": "TOGETHER_API_KEY",
        "type": "provider",
    },
    "fireworks": {
        "name": "Fireworks AI",
        "env_var": "FIREWORKS_API_KEY",
        "type": "provider",
    },
    "ollama": {
        "name": "Ollama",
        "env_var": "OLLAMA_BASE_URL",
        "type": "provider",
        "default_val": "http://localhost:11434",
    },
    "lmstudio": {
        "name": "LM Studio",
        "env_var": "LMSTUDIO_BASE_URL",
        "type": "provider",
        "default_val": "http://localhost:1234/v1",
    },
    # OAuth/Cloud providers
    "grok": {"name": "xAI Grok", "env_var": "GROK_API_KEY", "type": "oauth"},
    "qwen": {"name": "Alibaba Qwen", "env_var": "QWEN_API_KEY", "type": "oauth"},
    "claudecode": {
        "name": "Claude Code",
        "env_var": "CLAUDE_CODE_KEY",
        "type": "oauth",
    },
}


def ensure_predefined_in_db(db: Session):
    """Seed predefined providers metadata in SQLite if not present"""
    env_keys = load_env_keys()
    for pid, info in PREDEFINED_PROVIDERS.items():
        exists = (
            db.query(ProviderMetadata)
            .filter(ProviderMetadata.provider_id == pid)
            .first()
        )
        if not exists:
            # Derive status from whether credentials are actually configured
            env_val = env_keys.get(info["env_var"], "")
            has_key = bool(env_val)
            meta = ProviderMetadata(
                provider_id=pid,
                provider_name=info["name"],
                enabled=True,
                status="active" if has_key else "disconnected",
            )
            db.add(meta)
    db.commit()


@router.get("/")
def list_providers_and_keys(db: Session = Depends(get_db)):
    ensure_predefined_in_db(db)

    # Load raw env variables
    env_keys = load_env_keys()

    # Query SQLite metadata
    db_providers = db.query(ProviderMetadata).all()
    db_map = {p.provider_id: p for p in db_providers}

    response_list = []
    for pid, info in PREDEFINED_PROVIDERS.items():
        db_meta = db_map.get(pid)
        env_val = env_keys.get(info["env_var"], "")

        # Mask API keys for safety
        is_configured = bool(env_val)
        masked_val = ""
        if env_val:
            if env_val.startswith("http"):
                masked_val = env_val  # don't mask URLs
            else:
                masked_val = (
                    env_val[:6] + "..." + env_val[-4:]
                    if len(env_val) > 10
                    else "********"
                )

        response_list.append(
            {
                "provider_id": pid,
                "provider_name": info["name"],
                "type": info["type"],
                "env_var": info["env_var"],
                "configured": is_configured,
                "masked_value": masked_val,
                "enabled": db_meta.enabled if db_meta else True,
                "status": "active" if is_configured else "disconnected",
                "last_checked": db_meta.last_checked.isoformat()
                if db_meta and db_meta.last_checked
                else None,
            }
        )

    return response_list


@router.post("/{provider_id}")
def save_provider_config(
    provider_id: str, payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)
):
    """
    Payload contains:
    - value: The API key or Endpoint URL string
    - enabled: bool (optional)
    """
    if provider_id not in PREDEFINED_PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider not found")

    info = PREDEFINED_PROVIDERS[provider_id]
    env_var = info["env_var"]

    # Update environment file if value is sent
    if "value" in payload:
        new_val = payload["value"]
        if new_val:
            save_env_keys({env_var: new_val})

    # Update SQLite metadata
    db_meta = (
        db.query(ProviderMetadata)
        .filter(ProviderMetadata.provider_id == provider_id)
        .first()
    )
    if not db_meta:
        db_meta = ProviderMetadata(provider_id=provider_id, provider_name=info["name"])
        db.add(db_meta)

    if "enabled" in payload:
        db_meta.enabled = bool(payload["enabled"])

    db_meta.last_checked = datetime.datetime.utcnow()
    db_meta.status = (
        "active" if "value" in payload and payload["value"] else "disconnected"
    )
    db.commit()

    return {"status": "success", "provider_id": provider_id}


@router.post("/{provider_id}/test")
def test_provider_connection(provider_id: str, db: Session = Depends(get_db)):
    """Test the provider connection by making a real HTTP request."""
    import httpx

    if provider_id not in PREDEFINED_PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider not found")

    db_meta = (
        db.query(ProviderMetadata)
        .filter(ProviderMetadata.provider_id == provider_id)
        .first()
    )
    if not db_meta:
        db_meta = ProviderMetadata(
            provider_id=provider_id,
            provider_name=PREDEFINED_PROVIDERS[provider_id]["name"],
        )
        db.add(db_meta)

    db_meta.last_checked = datetime.datetime.utcnow()

    env_keys = load_env_keys()
    env_var = PREDEFINED_PROVIDERS[provider_id]["env_var"]
    api_key = env_keys.get(env_var, "")

    if not api_key:
        db_meta.status = "error"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"{env_var} is empty. Configure the key before testing.",
        )

    # Build endpoint URL based on provider type
    try:
        if provider_id == "ollama":
            resp = httpx.get(f"{api_key}/api/tags", timeout=5.0)
            resp.raise_for_status()
        elif provider_id == "lmstudio":
            resp = httpx.get(f"{api_key}/v1/models", timeout=5.0)
            resp.raise_for_status()
        elif api_key.startswith("http"):
            # Generic OpenAI-compatible endpoint
            resp = httpx.get(f"{api_key}/v1/models", timeout=5.0)
            resp.raise_for_status()
        else:
            # API key-based: try a lightweight models list call
            headers = {"Authorization": f"Bearer {api_key}"}
            base_urls = {
                "openai": "https://api.openai.com/v1/models",
                "anthropic": "https://api.anthropic.com/v1/models",
                "openrouter": "https://openrouter.ai/api/v1/models",
                "gemini": "https://generativelanguage.googleapis.com/v1/models",
                "google": "https://generativelanguage.googleapis.com/v1/models",
            }
            url = base_urls.get(provider_id, f"https://api.{provider_id}.com/v1/models")
            resp = httpx.get(url, headers=headers, timeout=5.0)
            resp.raise_for_status()

        db_meta.status = "active"
        db.commit()
        return {
            "status": "active",
            "last_checked": db_meta.last_checked.isoformat(),
        }
    except httpx.HTTPStatusError as e:
        logger.warning(
            f"Provider {provider_id} test failed with status {e.response.status_code}: {e.response.text[:200]}"
        )
        db_meta.status = "error"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Connection failed: HTTP {e.response.status_code} — {e.response.text[:100]}",
        )
    except httpx.RequestError as e:
        logger.warning(f"Provider {provider_id} test failed — network error: {e}")
        db_meta.status = "error"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reach provider: {e}",
        )


@router.post("/reload")
def trigger_reload():
    reload_settings()
    return {
        "status": "success",
        "message": "Runtime configuration reloaded successfully.",
    }
