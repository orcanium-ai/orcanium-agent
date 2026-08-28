"""Credential Pool — multi-key failover for model providers.

When a provider call fails with an auth/rate-limit error, the pool
automatically tries the next available credential for that provider.

Supports multiple API keys stored in ~/.orcanium/.env as:
    OPENAI_API_KEY_1, OPENAI_API_KEY_2, ...
    ANTHROPIC_API_KEY_1, ANTHROPIC_API_KEY_2, ...
"""

import logging
import os
import random
from typing import Any, Dict, List, Optional, Set

from orcanium.app.core.config import load_env_keys

logger = logging.getLogger(__name__)


class CredentialPool:
    """Manages multiple credentials per provider with failover."""

    def __init__(self):
        self._credentials: Dict[str, List[str]] = {}
        self._current_index: Dict[str, int] = {}
        self._failed: Set[str] = set()
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load all credentials from .env file.

        Supports numbered keys: OPENAI_API_KEY_1, OPENAI_API_KEY_2, etc.
        Falls back to single key: OPENAI_API_KEY
        """
        env = load_env_keys()

        # Provider key prefixes
        providers = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "groq": "GROQ_API_KEY",
            "together": "TOGETHER_API_KEY",
            "fireworks": "FIREWORKS_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }

        for provider, prefix in providers.items():
            keys: List[str] = []

            # Try numbered keys first
            for i in range(1, 11):
                key = env.get(f"{prefix}_{i}") or os.environ.get(f"{prefix}_{i}")
                if key:
                    keys.append(key)

            # Fall back to single key
            if not keys:
                key = env.get(prefix) or os.environ.get(prefix, "")
                if key:
                    keys.append(key)

            if keys:
                self._credentials[provider] = keys
                self._current_index[provider] = 0
                logger.debug(f"Loaded {len(keys)} credential(s) for {provider}")

    def get_credential(self, provider: str) -> Optional[str]:
        """Get the current credential for a provider."""
        keys = self._credentials.get(provider.lower())
        if not keys:
            return None
        idx = self._current_index.get(provider.lower(), 0)
        if idx >= len(keys):
            return None
        return keys[idx]

    def mark_failed(self, provider: str) -> Optional[str]:
        """Mark current credential as failed and rotate to next.

        Returns the new credential, or None if all exhausted.
        """
        prov = provider.lower()
        keys = self._credentials.get(prov)
        if not keys:
            return None

        self._failed.add(f"{prov}:{self._current_index.get(prov, 0)}")

        # Rotate to next available key
        for idx in range(len(keys)):
            if f"{prov}:{idx}" not in self._failed:
                self._current_index[prov] = idx
                logger.info(f"Rotated to credential {idx + 1}/{len(keys)} for {prov}")
                return keys[idx]

        # All keys exhausted — reset and try first one
        logger.warning(f"All credentials exhausted for {prov}. Resetting.")
        self._failed.clear()
        self._current_index[prov] = 0
        return keys[0] if keys else None

    def reset(self, provider: Optional[str] = None) -> None:
        """Reset failed credentials for a provider (or all)."""
        if provider:
            prov = provider.lower()
            self._failed = {f for f in self._failed if not f.startswith(f"{prov}:")}
            self._current_index[prov] = 0
        else:
            self._failed.clear()
            for prov in self._current_index:
                self._current_index[prov] = 0

    def get_status(self, provider: str) -> Dict[str, Any]:
        """Get credential status for a provider."""
        prov = provider.lower()
        keys = self._credentials.get(prov, [])
        current_idx = self._current_index.get(prov, 0)
        return {
            "provider": prov,
            "total_keys": len(keys),
            "current_index": current_idx,
            "current_key_preview": keys[current_idx][:12] + "..." if keys else None,
            "failed_keys": sum(1 for f in self._failed if f.startswith(f"{prov}:")),
            "all_exhausted": current_idx >= len(keys) if keys else True,
        }


# Singleton
credential_pool = CredentialPool()
