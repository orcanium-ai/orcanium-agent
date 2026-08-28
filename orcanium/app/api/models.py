from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from orcanium.app.core.config import load_system_config, update_system_config
from orcanium.app.domains.model.registry import clear_cache, discover_models
from orcanium.app.domains.provider.profiles import get_profile, list_profiles

router = APIRouter()


@router.get("/")
def get_model_providers_config():
    cfg = load_system_config()
    return cfg.get("model_providers", {})


@router.put("/update")
def update_model_providers_config(payload: Dict[str, Any] = Body(...)):
    """
    Payload matches:
    {
       "openai": {"api_key": "sk-..."},
       "ollama": {"base_url": "http://..."}
    }
    """
    try:
        current_cfg = load_system_config()
        providers = current_cfg.get("model_providers", {})

        for k, v in payload.items():
            if k in providers:
                providers[k].update(v)
            else:
                providers[k] = v

        update_system_config({"model_providers": providers})
        return {"status": "success", "model_providers": providers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profiles")
def list_provider_profiles():
    """List all registered provider profiles with their metadata."""
    profiles = list_profiles()
    return {
        pid: {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "auth_type": p.auth_type,
            "supports_vision": p.supports_vision,
            "supports_embeddings": p.supports_embeddings,
            "supports_tool_calling": p.supports_tool_calling,
            "supports_model_discovery": p.supports_model_discovery,
            "fallback_models": list(p.fallback_models),
            "env_var": p.env_var,
        }
        for pid, p in profiles.items()
    }


@router.get("/{provider_id}/models")
def list_provider_models(
    provider_id: str,
    force: bool = Query(False, description="Bypass cache"),
):
    """Discover available models for a provider."""
    try:
        profile = get_profile(provider_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    models = discover_models(provider_id, force=force)
    return {
        "provider_id": provider_id,
        "provider_name": profile.display_name,
        "models": models,
    }


@router.post("/{provider_id}/refresh")
def refresh_provider_models(provider_id: str):
    """Force-refresh the model cache for a provider."""
    try:
        profile = get_profile(provider_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    clear_cache(provider_id)
    models = discover_models(provider_id, force=True)
    return {
        "provider_id": provider_id,
        "provider_name": profile.display_name,
        "models": models,
    }
