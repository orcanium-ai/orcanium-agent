"""Model discovery — fetch available models from providers.

Each provider that supports model discovery exposes a /models endpoint.
This module fetches and caches those results.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from orcanium.app.domains.provider.profiles import get_profile, list_profiles

logger = logging.getLogger(__name__)

# Cache: {provider_id: {models: [...], fetched_at: timestamp}}
_model_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def discover_models(provider_id: str, force: bool = False) -> List[Dict[str, str]]:
    """Fetch available models for a provider.

    Returns list of {id, name, ...} dicts.
    Uses cache with 5-minute TTL.
    """
    now = time.time()

    # Check cache
    if not force and provider_id in _model_cache:
        cached = _model_cache[provider_id]
        if now - cached.get("fetched_at", 0) < _CACHE_TTL_SECONDS:
            return cached["models"]

    try:
        profile = get_profile(provider_id)
    except KeyError:
        return []

    if not profile.supports_model_discovery:
        # Return fallback models
        return [{"id": m, "name": m} for m in profile.fallback_models]

    models_url = profile.get_models_url()
    if not models_url:
        return [{"id": m, "name": m} for m in profile.fallback_models]

    # Fetch from provider (with auth headers if available)
    try:
        headers = {}
        if profile.env_var:
            import os
            api_key = os.getenv(profile.env_var)
            if api_key and profile.auth_type == "api_key":
                headers["Authorization"] = f"Bearer {api_key}"
        with httpx.Client() as client:
            resp = client.get(models_url, headers=headers or None, timeout=15)
            if resp.status_code == 200:
                models = _parse_models_response(provider_id, resp.json())
                _model_cache[provider_id] = {
                    "models": models,
                    "fetched_at": now,
                }
                return models
    except Exception as e:
        logger.warning(f"Model discovery failed for {provider_id}: {e}")

    # Fallback
    return [{"id": m, "name": m} for m in profile.fallback_models]


def _parse_models_response(provider_id: str, data: Any) -> List[Dict[str, str]]:
    """Parse provider-specific /models response into standard format."""
    models = []

    if provider_id == "openai":
        # OpenAI: data.data[].id
        for item in data.get("data", []):
            models.append({"id": item["id"], "name": item["id"]})

    elif provider_id == "ollama":
        # Ollama: models[].name
        for item in data.get("models", []):
            models.append({"id": item["name"], "name": item["name"]})

    elif provider_id == "openai_compatible":
        # OpenAI-compatible: data[].id
        for item in data.get("data", []):
            models.append({"id": item["id"], "name": item.get("id", item["id"])})

    else:
        # Generic: try common patterns
        if isinstance(data, list):
            for item in data:
                mid = item.get("id") or item.get("name", "")
                if mid:
                    models.append({"id": mid, "name": mid})
        elif isinstance(data, dict):
            for item in data.get("data", []):
                mid = item.get("id") or item.get("name", "")
                if mid:
                    models.append({"id": mid, "name": mid})

    return models


def get_cached_models(provider_id: str) -> List[Dict[str, str]]:
    """Return cached models without fetching."""
    cached = _model_cache.get(provider_id)
    if cached:
        return cached["models"]
    return []


def clear_cache(provider_id: Optional[str] = None):
    """Clear model cache for a specific provider or all."""
    if provider_id:
        _model_cache.pop(provider_id, None)
    else:
        _model_cache.clear()
