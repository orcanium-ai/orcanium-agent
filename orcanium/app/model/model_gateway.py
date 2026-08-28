import os
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from orcanium.app.core.config import load_env_keys, load_system_config
from orcanium.app.core.trace import trace, trace_id
from orcanium.app.domains.system.errors import EmbeddingError
from orcanium.app.model.providers import (
    AnthropicProvider,
    BaseProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
)

logger = logging.getLogger(__name__)

# Thread-local context for LLM call purpose tracking
_tls = threading.local()


def set_llm_purpose(purpose: str) -> None:
    """Set the purpose tag for subsequent LLM calls on this thread.

    Purpose must be one of:
        PRIMARY_RESPONSE, TITLE_GENERATION, MEMORY_REVIEW,
        SKILL_REVIEW, KNOWLEDGE_REVIEW, OTHER
    """
    _tls.llm_purpose = purpose


def set_llm_context(agent_id: str, session_id: Optional[str] = None) -> None:
    """Set the agent/session key used by the LLM request scheduler."""
    _tls.agent_id = agent_id
    _tls.session_id = session_id


def clear_llm_context() -> None:
    """Clear scheduler context for this thread."""
    for name in ("agent_id", "session_id", "llm_purpose"):
        if hasattr(_tls, name):
            delattr(_tls, name)


class ModelGateway:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._providers_loaded_at = 0.0  # monotonic timestamp
        self._load_providers()

    def _load_providers(self):
        # Read keys from ~/.orcanium/.env (reliable source of truth)
        env = load_env_keys()

        # OpenAI
        self._providers["openai"] = OpenAIProvider(
            api_key=env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        )

        # Anthropic
        self._providers["anthropic"] = AnthropicProvider(
            api_key=env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"),
        )

        # Gemini
        self._providers["gemini"] = GeminiProvider(
            api_key=env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY"),
        )

        # Ollama
        ollama_url = env.get("OLLAMA_BASE_URL") or os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self._providers["ollama"] = OllamaProvider(base_url=ollama_url)

        # OpenRouter
        self._providers["openrouter"] = OpenRouterProvider(
            api_key=env.get("OPENROUTER_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY"),
        )

        # DeepSeek (OpenAI-compatible)
        self._providers["deepseek"] = OpenAIProvider(
            api_key=env.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        )

        # Groq (OpenAI-compatible)
        self._providers["groq"] = OpenAIProvider(
            api_key=env.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )

        # Together AI (OpenAI-compatible)
        self._providers["together"] = OpenAIProvider(
            api_key=env.get("TOGETHER_API_KEY") or os.environ.get("TOGETHER_API_KEY"),
            base_url="https://api.together.xyz/v1",
        )

        # Fireworks AI (OpenAI-compatible)
        self._providers["fireworks"] = OpenAIProvider(
            api_key=env.get("FIREWORKS_API_KEY") or os.environ.get("FIREWORKS_API_KEY"),
            base_url="https://api.fireworks.ai/inference/v1",
        )

        # LM Studio (local OpenAI-compatible, no key required)
        lmstudio_url = env.get("LMSTUDIO_BASE_URL") or os.environ.get(
            "LMSTUDIO_BASE_URL", "http://localhost:1234/v1"
        )
        self._providers["lmstudio"] = OpenAIProvider(
            api_key="lmstudio",
            base_url=lmstudio_url,
        )

        # Google (same as Gemini)
        self._providers["google"] = GeminiProvider(
            api_key=env.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
        )

    def _ensure_providers_loaded(self) -> None:
        """Reload providers at most once per 30s — env changes propagate slowly."""
        if time.monotonic() - self._providers_loaded_at > 30.0:
            self._load_providers()
            self._providers_loaded_at = time.monotonic()

    def _force_reload_providers(self) -> None:
        """Force reload — call after credential rotation."""
        self._load_providers()
        self._providers_loaded_at = time.monotonic()

    def generate(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: str,
        config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict]] = None,
    ) -> str:
        """Unified chat/generation interface across multiple providers."""
        return self.generate_with_usage(messages, provider, model, config, tools)[
            "text"
        ]

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: str,
        config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict]] = None,
        delta_callback=None,
    ) -> Dict[str, Any]:
        """Streaming generation — calls delta_callback(delta_text) for each token chunk.

        Args:
            messages: Chat messages
            provider: Provider name
            model: Model name
            config: Model config
            tools: Tool definitions (optional)
            delta_callback: Called with each text delta string

        Returns:
            dict with "text" (full response), "input_tokens", "output_tokens"
        """
        self._ensure_providers_loaded()

        prov_name = provider.lower()
        if prov_name not in self._providers:
            raise ValueError(f"Unsupported provider: {provider}")

        from orcanium.app.domains.provider.credential_pool import credential_pool

        max_retries = len(credential_pool._credentials.get(prov_name, [])) or 1
        last_error = None

        def _call_provider() -> Dict[str, Any]:
            nonlocal last_error
            for attempt in range(max_retries):
                try:
                    prov = self._providers[prov_name]
                    if hasattr(prov, "generate_stream"):
                        return prov.generate_stream(
                            messages, model, config or {},
                            tools=tools, delta_callback=delta_callback,
                        )
                    result = prov.generate_with_usage(
                        messages, model, config or {}, tools=tools,
                    )
                    full_text = result.get("text", "")
                    if delta_callback:
                        delta_callback(full_text)
                    return result
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    if any(
                        term in error_str
                        for term in [
                            "401", "403", "429",
                            "unauthorized", "rate limit",
                            "quota", "insufficient_quota",
                        ]
                    ):
                        new_cred = credential_pool.mark_failed(prov_name)
                        if new_cred and attempt < max_retries - 1:
                            self._force_reload_providers()
                            continue
                    raise last_error
            raise last_error or ValueError(f"All credentials exhausted for {provider}")

        return self._run_scheduled(_call_provider)

    def generate_with_usage(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: str,
        config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict]] = None,
    ) -> dict:
        """Generate and return {text, input_tokens, output_tokens}. Optionally pass tool definitions."""
        _tid = trace_id()
        _t0 = time.time()
        purpose = getattr(_tls, "llm_purpose", "OTHER")
        trace("ENTER", "generate_with_usage", request_id=_tid, purpose=purpose, extra=f"provider={provider} model={model}")
        self._ensure_providers_loaded()

        prov_name = provider.lower()
        if prov_name not in self._providers:
            raise ValueError(f"Unsupported or unconfigured model provider: {provider}")

        # Credential pool recovery
        from orcanium.app.domains.provider.credential_pool import credential_pool

        max_retries = len(credential_pool._credentials.get(prov_name, [])) or 1
        last_error = None

        def _call_provider() -> dict:
            nonlocal last_error
            for attempt in range(max_retries):
                try:
                    result = self._providers[prov_name].generate_with_usage(
                        messages,
                        model,
                        config or {},
                        tools=tools,
                    )
                    trace("EXIT", "generate_with_usage", request_id=_tid, purpose=purpose, elapsed_ms=(time.time() - _t0) * 1000)
                    return result
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    # Only rotate on auth/rate-limit errors
                    if any(
                        term in error_str
                        for term in [
                            "401",
                            "403",
                            "429",
                            "unauthorized",
                            "rate limit",
                            "quota",
                            "insufficient_quota",
                        ]
                    ):
                        new_cred = credential_pool.mark_failed(prov_name)
                        if new_cred and attempt < max_retries - 1:
                            logger.info(
                                f"Credential failed for {prov_name}, rotating (attempt {attempt + 1}/{max_retries})"
                            )
                            # Re-load providers with new credential
                            self._force_reload_providers()
                            continue
                    raise last_error

            raise last_error or ValueError(f"All credentials exhausted for {provider}")

        return self._run_scheduled(_call_provider)

    def _run_scheduled(self, fn):
        agent_id = getattr(_tls, "agent_id", None)
        session_id = getattr(_tls, "session_id", None)
        purpose = getattr(_tls, "llm_purpose", "OTHER")
        if not agent_id:
            return fn()

        from orcanium.app.domains.agent.request_scheduler import (
            DEFAULT_LLM_TIMEOUT_SECONDS,
            agent_request_scheduler,
        )

        return agent_request_scheduler.run(
            agent_id=agent_id,
            session_id=session_id,
            purpose=purpose,
            fn=fn,
            timeout=DEFAULT_LLM_TIMEOUT_SECONDS,
        )

    def generate_embeddings(self, text: str, provider: str, model: str) -> List[float]:
        """Unified embeddings generation interface.

        Raises EmbeddingError if all attempts fail — never returns zero vectors.
        """
        self._ensure_providers_loaded()

        prov_name = provider.lower()
        if prov_name not in self._providers:
            prov_name = "openai"

        prov = self._providers[prov_name]
        return prov.generate_embeddings(text, model)


model_gateway = ModelGateway()
