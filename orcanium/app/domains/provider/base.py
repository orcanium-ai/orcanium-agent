"""Declarative provider profile — declares everything about an inference provider.

A ProviderProfile describes the provider's behavior, auth, endpoints,
model discovery, and supported features.  It does NOT own client
construction or streaming — those stay on the provider implementations.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderProfile:
    """Declarative profile for a model inference provider."""

    # ── Identity ─────────────────────────────────────────
    id: str
    name: str
    display_name: str = ""

    # ── Auth ─────────────────────────────────────────────
    env_var: str = ""
    auth_type: str = "api_key"  # api_key, oauth, none

    # ── Endpoints ────────────────────────────────────────
    base_url: str = ""
    models_url: str = ""
    chat_completions_path: str = "/v1/chat/completions"

    # ── Model discovery ──────────────────────────────────
    fallback_models: tuple = ()
    supports_model_discovery: bool = True

    # ── Capabilities ─────────────────────────────────────
    supports_vision: bool = False
    supports_tool_calling: bool = True
    supports_embeddings: bool = False
    supports_streaming: bool = False
    default_max_tokens: int = 2048

    # ── Provider class path for dynamic import ───────────
    provider_class: str = ""  # e.g. "orcanium.app.model.providers.OpenAIProvider"

    def get_models_url(self) -> str:
        """Return the URL to fetch available models.

        Uses the env var override (if set) for providers like Ollama
        whose base_url is user-configurable.
        """
        if self.models_url:
            return self.models_url

        # Resolve effective base URL — check env var first, fallback to profile
        effective_base = self.base_url
        if self.env_var:
            import os

            # Check os.environ first (loaded from .env at startup), then .env file
            env_val = os.environ.get(self.env_var, "")
            if not env_val:
                try:
                    from orcanium.app.core.config import load_env_keys

                    env_keys = load_env_keys()
                    env_val = env_keys.get(self.env_var, "")
                except Exception:
                    pass
            if env_val:
                effective_base = env_val

        if effective_base:
            base = effective_base.rstrip("/")
            # Ollama uses /api/tags instead of /models
            if self.id == "ollama":
                return f"{base}/api/tags"
            return f"{base}/models"
        return ""
