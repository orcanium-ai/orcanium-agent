"""Built-in provider profile definitions.

Each provider is described by a ProviderProfile dataclass that declares
everything about the provider: auth, endpoints, model discovery, and
supported capabilities.
"""

from orcanium.app.domains.provider.base import ProviderProfile

# ── Profile registry ───────────────────────────────────────

PROVIDER_PROFILES: dict = {}


def register(profile: ProviderProfile):
    PROVIDER_PROFILES[profile.id] = profile


def get_profile(provider_id: str) -> ProviderProfile:
    """Look up a profile by ID, raising KeyError if not found."""
    if provider_id not in PROVIDER_PROFILES:
        raise KeyError(f"Unknown provider: {provider_id}")
    return PROVIDER_PROFILES[provider_id]


def list_profiles() -> dict:
    """Return all registered profiles keyed by provider ID."""
    return dict(PROVIDER_PROFILES)


# ── Built-in provider definitions ──────────────────────────

register(
    ProviderProfile(
        id="openai",
        name="OpenAI",
        display_name="OpenAI",
        env_var="OPENAI_API_KEY",
        base_url="https://api.openai.com",
        supports_vision=True,
        supports_embeddings=True,
        auth_type="api_key",
        supports_model_discovery=True,
        models_url="https://api.openai.com/v1/models",
        fallback_models=("gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"),
        provider_class="orcanium.app.model.providers.OpenAIProvider",
    )
)

register(
    ProviderProfile(
        id="anthropic",
        name="Anthropic",
        display_name="Anthropic",
        env_var="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com",
        supports_vision=True,
        supports_embeddings=False,
        fallback_models=(
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ),
        provider_class="orcanium.app.model.providers.AnthropicProvider",
    )
)

register(
    ProviderProfile(
        id="gemini",
        name="Gemini",
        display_name="Google Gemini",
        env_var="GEMINI_API_KEY",
        models_url="https://generativelanguage.googleapis.com/v1beta/models",
        supports_vision=True,
        supports_embeddings=True,
        fallback_models=("gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"),
        provider_class="orcanium.app.model.providers.GeminiProvider",
    )
)

register(
    ProviderProfile(
        id="ollama",
        name="Ollama",
        display_name="Ollama (Local)",
        env_var="OLLAMA_BASE_URL",
        base_url="http://localhost:11434",
        auth_type="none",
        supports_embeddings=True,
        supports_tool_calling=False,
        supports_model_discovery=True,
        fallback_models=("llama3", "mixtral", "codellama", "nomic-embed-text"),
        provider_class="orcanium.app.model.providers.OllamaProvider",
    )
)

register(
    ProviderProfile(
        id="openrouter",
        name="OpenRouter",
        display_name="OpenRouter",
        env_var="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api",
        supports_vision=True,
        fallback_models=(
            "meta-llama/llama-3-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "openai/gpt-4o",
        ),
        provider_class="orcanium.app.model.providers.OpenRouterProvider",
    )
)

register(
    ProviderProfile(
        id="openai_compatible",
        name="OpenAI-Compatible",
        display_name="OpenAI-Compatible API",
        env_var="",
        base_url="",
        auth_type="api_key",
        supports_vision=True,
        supports_model_discovery=True,
        fallback_models=("gpt-4o", "gpt-4o-mini"),
        provider_class="orcanium.app.model.providers.OpenAIProvider",
    )
)

register(
    ProviderProfile(
        id="deepseek",
        name="DeepSeek",
        display_name="DeepSeek",
        env_var="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
        fallback_models=("deepseek-chat", "deepseek-reasoner"),
        supports_vision=False,
        supports_embeddings=False,
        provider_class="orcanium.app.model.providers.OpenAIProvider",
    )
)

register(
    ProviderProfile(
        id="groq",
        name="Groq",
        display_name="Groq Cloud",
        env_var="GROQ_API_KEY",
        base_url="https://api.groq.com/openai",
        fallback_models=("llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"),
        supports_vision=True,
        supports_embeddings=False,
        provider_class="orcanium.app.model.providers.OpenAIProvider",
    )
)

register(
    ProviderProfile(
        id="together",
        name="Together AI",
        display_name="Together AI",
        env_var="TOGETHER_API_KEY",
        base_url="https://api.together.xyz",
        fallback_models=(
            "meta-llama/Llama-3-70b-chat-hf",
            "meta-llama/Llama-3-8b-chat-hf",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
        ),
        supports_vision=True,
        supports_embeddings=False,
        provider_class="orcanium.app.model.providers.OpenAIProvider",
    )
)

register(
    ProviderProfile(
        id="fireworks",
        name="Fireworks AI",
        display_name="Fireworks AI",
        env_var="FIREWORKS_API_KEY",
        base_url="https://api.fireworks.ai/inference",
        fallback_models=(
            "accounts/fireworks/models/llama-v3p1-70b-instruct",
            "accounts/fireworks/models/llama-v3p1-8b-instruct",
            "accounts/fireworks/models/mixtral-8x7b-instruct",
        ),
        supports_vision=True,
        supports_embeddings=True,
        provider_class="orcanium.app.model.providers.OpenAIProvider",
    )
)

register(
    ProviderProfile(
        id="lmstudio",
        name="LM Studio",
        display_name="LM Studio (Local)",
        env_var="LMSTUDIO_BASE_URL",
        base_url="http://localhost:1234/v1",
        auth_type="none",
        supports_model_discovery=True,
        fallback_models=("local-model",),
        supports_vision=True,
        supports_embeddings=False,
        provider_class="orcanium.app.model.providers.OpenAIProvider",
    )
)

register(
    ProviderProfile(
        id="google",
        name="Google",
        display_name="Google Gemini",
        env_var="GOOGLE_API_KEY",
        base_url="https://generativelanguage.googleapis.com",
        models_url="https://generativelanguage.googleapis.com/v1beta/models",
        supports_vision=True,
        supports_embeddings=True,
        fallback_models=("gemini-1.5-flash", "gemini-1.5-pro"),
        provider_class="orcanium.app.model.providers.GeminiProvider",
    )
)
