"""Custom exceptions for Orcanium runtime domains."""


class OrcaniumError(Exception):
    """Base exception for all Orcanium errors."""

    pass


class EmbeddingError(OrcaniumError):
    """Raised when embedding generation fails after all retries.

    This is a critical error — callers must NOT silently fall back
    to zero vectors.  Embeddings that return all zeros will silently
    degrade search quality.  This exception forces the caller to
    handle the failure explicitly.
    """

    def __init__(self, provider: str = "", message: str = ""):
        self.provider = provider
        self.message = (
            message or f"Embedding generation failed for provider '{provider}'"
        )
        super().__init__(self.message)


class ProviderError(OrcaniumError):
    """Raised when a model provider is unreachable or returns an error."""

    def __init__(self, provider: str = "", message: str = ""):
        self.provider = provider
        self.message = message or f"Provider '{provider}' error"
        super().__init__(self.message)


class AgentError(OrcaniumError):
    """Raised when an agent operation fails."""

    pass


class HealthCheckError(OrcaniumError):
    """Raised when a health check fails."""

    def __init__(self, component: str = "", message: str = ""):
        self.component = component
        self.message = message or f"Health check failed for '{component}'"
        super().__init__(self.message)
