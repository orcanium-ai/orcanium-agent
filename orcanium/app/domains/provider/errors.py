"""Provider Error Model — unified error types for all providers.

Pipeline handles only normalized errors. Never provider-specific exceptions.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class ProviderErrorType(str, enum.Enum):
    """Normalized provider error types."""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_FAILED = "auth_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_MODEL = "invalid_model"
    TOOL_CALL_FAILED = "tool_call_failed"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


# Provider errors that are safe to retry
_RETRYABLE = {
    ProviderErrorType.TIMEOUT,
    ProviderErrorType.RATE_LIMIT,
    ProviderErrorType.PROVIDER_UNAVAILABLE,
    ProviderErrorType.NETWORK_ERROR,
}


@dataclass
class ProviderError:
    """Normalized provider error — pipeline handles only this type."""
    type: ProviderErrorType = ProviderErrorType.UNKNOWN
    message: str = ""
    provider: str = ""
    model: str = ""
    retryable: bool = False

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "message": self.message,
            "provider": self.provider,
            "model": self.model,
            "retryable": self.retryable,
        }


def normalize_error(exception: Exception, provider: str = "", model: str = "") -> ProviderError:
    """Map any provider exception to a normalized ProviderError."""
    msg = str(exception).lower()

    if isinstance(exception, TimeoutError):
        return ProviderError(ProviderErrorType.TIMEOUT, str(exception), provider, model, retryable=True)

    if "rate" in msg and "limit" in msg:
        return ProviderError(ProviderErrorType.RATE_LIMIT, str(exception), provider, model, retryable=True)

    if any(kw in msg for kw in ["auth", "unauthorized", "forbidden", "401", "403", "api_key"]):
        return ProviderError(ProviderErrorType.AUTH_FAILED, str(exception), provider, model)

    if any(kw in msg for kw in ["connection", "dns", "refused", "unreachable"]):
        return ProviderError(ProviderErrorType.NETWORK_ERROR, str(exception), provider, model, retryable=True)

    if "model" in msg and any(kw in msg for kw in ["not found", "invalid", "unavailable"]):
        return ProviderError(ProviderErrorType.INVALID_MODEL, str(exception), provider, model)

    if "tool" in msg and any(kw in msg for kw in ["call", "exec", "invalid"]):
        return ProviderError(ProviderErrorType.TOOL_CALL_FAILED, str(exception), provider, model)

    return ProviderError(ProviderErrorType.UNKNOWN, str(exception), provider, model, retryable=False)
