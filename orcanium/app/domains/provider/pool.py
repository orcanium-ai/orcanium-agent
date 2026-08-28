"""Credential pool — multi-key rotation for providers.

Allows storing multiple API keys per provider with round-robin
rotation on each LLM call.  Keys are stored in ~/.orcanium/.env only.
"""

import logging
import os
import threading
from typing import Dict, List, Optional

from orcanium.app.core.config import load_env_keys, save_env_keys

logger = logging.getLogger(__name__)


class CredentialPool:
    """Manages multiple API keys per provider with round-robin rotation."""

    def __init__(self):
        self._index: Dict[str, int] = {}
        self._lock = threading.Lock()

    def get_keys(self, provider_id: str) -> List[str]:
        """Return all API keys for a given provider.

        Looks for env vars named {PROVIDER}_API_KEY_0, _1, _2, etc.
        Falls back to {PROVIDER}_API_KEY if no numbered keys exist.
        """
        env_key = self._env_var_name(provider_id)
        keys = []

        # Try numbered keys first (pool rotation)
        for i in range(10):
            numbered_key = f"{env_key}_{i}"
            val = os.environ.get(numbered_key) or ""
            if val:
                keys.append(val)

        # Fall back to single key
        if not keys:
            val = os.environ.get(env_key) or ""
            if val:
                keys.append(val)

        return keys

    def get_next_key(self, provider_id: str) -> Optional[str]:
        """Get the next API key for a provider using round-robin.

        Returns None if no keys are configured.
        """
        keys = self.get_keys(provider_id)
        if not keys:
            return None

        with self._lock:
            idx = self._index.get(provider_id, 0)
            key = keys[idx % len(keys)]
            self._index[provider_id] = (idx + 1) % len(keys)

        return key

    def add_key(self, provider_id: str, key: str):
        """Add a new API key for a provider.

        Finds the next available numbered slot and saves it.
        """
        env_key = self._env_var_name(provider_id)
        current_keys = load_env_keys()

        # Find the next available slot
        for i in range(10):
            slot = f"{env_key}_{i}" if i > 0 else env_key
            if slot not in current_keys or not current_keys.get(slot):
                current_keys[slot] = key
                save_env_keys(current_keys)
                logger.info(f"Added key for {provider_id} in slot {slot}")
                return

        logger.warning(f"No available slots for {provider_id} keys (max 10)")

    def remove_key(self, provider_id: str, index: int = 0):
        """Remove a key by index (0 = primary, 1+ = pooled)."""
        env_key = self._env_var_name(provider_id)
        slot = f"{env_key}_{index}" if index > 0 else env_key

        current_keys = load_env_keys()
        if slot in current_keys:
            del current_keys[slot]
            save_env_keys(current_keys)
            logger.info(f"Removed key slot {slot} for {provider_id}")

    def key_count(self, provider_id: str) -> int:
        return len(self.get_keys(provider_id))

    @staticmethod
    def _env_var_name(provider_id: str) -> str:
        """Convert 'openai' to 'OPENAI_API_KEY'."""
        mapping = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "groq": "GROQ_API_KEY",
            "together": "TOGETHER_API_KEY",
            "fireworks": "FIREWORKS_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        return mapping.get(provider_id, f"{provider_id.upper()}_API_KEY")


# Global singleton
credential_pool = CredentialPool()
