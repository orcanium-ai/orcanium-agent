import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI

from orcanium.app.core.config import settings
from orcanium.app.domains.system.errors import EmbeddingError, ProviderError

logger = logging.getLogger(__name__)

_EMBEDDING_RETRIES = 3
_EMBEDDING_RETRY_DELAY_S = 1.0


def _embedding_retry(provider_name: str, fn, *args, **kwargs) -> List[float]:
    """Call fn with retries. Raises EmbeddingError after exhaustion."""
    last_err = None
    for attempt in range(_EMBEDDING_RETRIES):
        try:
            result = fn(*args, **kwargs)
            if result and any(v != 0.0 for v in result):
                return result
            # All-zero vectors are treated as failure — they silently degrade search
            last_err = ValueError("Embedding returned all-zero vector")
        except Exception as e:
            last_err = e
            if attempt < _EMBEDDING_RETRIES - 1:
                time.sleep(_EMBEDDING_RETRY_DELAY_S * (attempt + 1))
    raise EmbeddingError(provider=provider_name, message=str(last_err))


class BaseProvider:
    def generate(
        self, messages: List[Dict[str, str]], model: str, config: Dict[str, Any]
    ) -> str:
        raise NotImplementedError()

    def generate_with_usage(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        tools: Optional[List[Dict]] = None,
    ) -> dict:
        """Return {text, input_tokens, output_tokens}. Falls back to generate()."""
        text = self.generate(messages, model, config)
        return {"text": text, "input_tokens": None, "output_tokens": None}

    def generate_embeddings(self, text: str, model: str) -> List[float]:
        raise NotImplementedError()


class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url

    def _get_client(self) -> OpenAI:
        if not self.api_key:
            raise ValueError(f"{self.__class__.__name__}: API key not set")
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def generate(
        self, messages: List[Dict[str, str]], model: str, config: Dict[str, Any]
    ) -> str:
        return self.generate_with_usage(messages, model, config)["text"]

    def generate_with_usage(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        tools: Optional[List[Dict]] = None,
    ) -> dict:
        client = self._get_client()
        temp = config.get("temperature", 0.7)
        max_tokens_val = config.get("max_tokens", 2048)

        kwargs = dict(
            model=model or "gpt-4-turbo",
            messages=messages,  # type: ignore
            temperature=temp,
        )
        # o-series and newer models require max_completion_tokens
        _model_prefix = (model or "").split("/")[-1].lstrip().lower()
        if _model_prefix.startswith(("o1", "o3", "o4", "gpt-5", "gpt-4.1", "gpt-4o-transcribe", "o1-pro")):
            kwargs["max_completion_tokens"] = max_tokens_val
        else:
            kwargs["max_tokens"] = max_tokens_val
        if tools is not None:
            kwargs["tools"] = tools

        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        usage = response.usage
        return {
            "text": text,
            "input_tokens": usage.prompt_tokens if usage else None,
            "output_tokens": usage.completion_tokens if usage else None,
        }

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        tools: Optional[List[Dict]] = None,
        delta_callback=None,
    ) -> Dict[str, Any]:
        """Streaming generation with token-level delta callbacks."""
        client = self._get_client()
        temp = config.get("temperature", 0.7)
        max_tokens_val = config.get("max_tokens", 2048)

        kwargs = dict(
            model=model or "gpt-4-turbo",
            messages=messages,
            temperature=temp,
            stream=True,
        )
        # o-series and newer models require max_completion_tokens
        _model_prefix = (model or "").split("/")[-1].lstrip().lower()
        if _model_prefix.startswith(("o1", "o3", "o4", "gpt-5", "gpt-4.1", "gpt-4o-transcribe", "o1-pro")):
            kwargs["max_completion_tokens"] = max_tokens_val
        else:
            kwargs["max_tokens"] = max_tokens_val
        _reasoning_effort = config.get("reasoning_effort", "").strip().lower()
        if _model_prefix.startswith(("o1", "o3", "o4", "gpt-5")) and _reasoning_effort:
            kwargs["reasoning_effort"] = _reasoning_effort
        if tools is not None:
            kwargs["tools"] = tools

        full_text = ""
        input_tokens = 0
        output_tokens = 0

        stream = client.chat.completions.create(**kwargs)
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text += delta.content
                if delta_callback:
                    delta_callback(delta.content)
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0

        return {
            "text": full_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    def generate_embeddings(
        self, text: str, model: str = "text-embedding-3-small"
    ) -> List[float]:
        client = self._get_client()
        return _embedding_retry(
            "openai",
            lambda: (
                client.embeddings.create(input=[text], model=model).data[0].embedding
            ),
        )


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY

    def generate(
        self, messages: List[Dict[str, str]], model: str, config: Dict[str, Any]
    ) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API key not set")

        # Standardize messages for Anthropic (separate system message, if any, and role format)
        system_msg = ""
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            else:
                anthropic_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": model or "claude-3-haiku-20240307",
            "messages": anthropic_messages,
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 2048),
        }
        if system_msg:
            payload["system"] = system_msg.strip()

        with httpx.Client() as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            if resp.status_code != 200:
                raise Exception(f"Anthropic error: {resp.text}")
            result = resp.json()
            return result["content"][0]["text"]

    def generate_embeddings(self, text: str, model: str) -> List[float]:
        # Anthropic doesn't have an embedding model.
        raise EmbeddingError(
            provider="anthropic",
            message="Anthropic does not provide embedding models. Use OpenAI or Ollama for embeddings.",
        )


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def generate(
        self, messages: List[Dict[str, str]], model: str, config: Dict[str, Any]
    ) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key not set")

        # Convert standard chat messages into Gemini API structure
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = {"parts": [{"text": msg["content"]}]}
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-1.5-flash'}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.get("temperature", 0.7),
                "maxOutputTokens": config.get("max_tokens", 2048),
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        with httpx.Client() as client:
            resp = client.post(url, json=payload, timeout=60.0)
            if resp.status_code != 200:
                raise Exception(f"Gemini API error: {resp.text}")
            data = resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return ""

    def generate_embeddings(
        self, text: str, model: str = "text-embedding-004"
    ) -> List[float]:
        if not self.api_key:
            raise EmbeddingError(provider="gemini", message="Gemini API key not set")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={self.api_key}"
        payload = {"model": f"models/{model}", "content": {"parts": [{"text": text}]}}

        def _call():
            with httpx.Client() as client:
                resp = client.post(url, json=payload, timeout=30.0)
                if resp.status_code == 200:
                    return resp.json()["embedding"]["values"]
                raise ProviderError(provider="gemini", message=resp.text)

        return _embedding_retry("gemini", _call)


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL

    def generate(
        self, messages: List[Dict[str, str]], model: str, config: Dict[str, Any]
    ) -> str:
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": model or "llama3",
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.get("temperature", 0.7),
                "num_predict": config.get("max_tokens", 2048),
            },
        }
        with httpx.Client() as client:
            resp = client.post(url, json=payload, timeout=120.0)
            if resp.status_code != 200:
                raise Exception(f"Ollama error: {resp.text}")
            return resp.json()["message"]["content"]

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        tools: Optional[List[Dict]] = None,
        delta_callback=None,
    ) -> Dict[str, Any]:
        """Streaming generation via Ollama SSE endpoint.

        Ollama's /api/chat with stream=true returns one JSON object per line.
        """
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": model or "llama3",
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": config.get("temperature", 0.7),
                "num_predict": config.get("max_tokens", 2048),
            },
        }
        full_text = ""
        with httpx.Client() as client:
            with client.stream("POST", url, json=payload, timeout=120.0) as resp:
                if resp.status_code != 200:
                    raise Exception(f"Ollama stream error: {resp.status_code}")
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        full_text += delta
                        if delta_callback:
                            delta_callback(delta)
                    if chunk.get("done", False):
                        break
        return {
            "text": full_text,
            "input_tokens": None,
            "output_tokens": None,
        }

    def generate_embeddings(
        self, text: str, model: str = "nomic-embed-text"
    ) -> List[float]:
        url = f"{self.base_url.rstrip('/')}/api/embeddings"
        payload = {"model": model, "prompt": text}

        def _call():
            with httpx.Client() as client:
                resp = client.post(url, json=payload, timeout=30.0)
                if resp.status_code == 200:
                    result = resp.json()["embedding"]
                    if any(v != 0.0 for v in result):
                        return result
                    raise ValueError("Ollama returned all-zero embedding")
                raise ProviderError(provider="ollama", message=resp.text)

        return _embedding_retry("ollama", _call)


class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY

    def generate(
        self, messages: List[Dict[str, str]], model: str, config: Dict[str, Any]
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API key not set")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "meta-llama/llama-3-8b-instruct:free",
            "messages": messages,
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 2048),
        }
        with httpx.Client() as client:
            resp = client.post(url, json=payload, headers=headers, timeout=90.0)
            if resp.status_code != 200:
                raise Exception(f"OpenRouter error: {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    def generate_embeddings(self, text: str, model: str) -> List[float]:
        # OpenRouter doesn't provide dedicated embedding endpoints.
        raise EmbeddingError(
            provider="openrouter",
            message="OpenRouter does not provide embedding models. Use OpenAI or Ollama for embeddings.",
        )
