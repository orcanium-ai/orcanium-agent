"""Shared resolution of local agent model and provider configuration."""

from __future__ import annotations

from typing import Any, Callable


def configured_model(config: dict[str, Any], *, fallback: str = "") -> str:
    """Return the configured model without interpreting interface-specific env vars."""
    model_config = config.get("model", "")
    if isinstance(model_config, dict):
        return str(model_config.get("default", "") or model_config.get("model", "") or fallback).strip()
    if isinstance(model_config, str):
        return model_config.strip() or fallback
    return fallback


def resolve_startup_model_and_provider(
    config: dict[str, Any],
    *,
    model_override: str = "",
    provider_override: str = "",
    inference_model: str = "",
    inference_provider: str = "",
    fallback_model: str = "",
    detect_provider: Callable[[str, str], tuple[str, str] | None] | None = None,
) -> tuple[str, str | None]:
    """Resolve a startup model/provider pair with one explicit precedence order.

    Interactive interfaces may pass their own process-level overrides; config
    remains the fallback. Provider auto-detection is injected so this pure
    runtime module does not import the CLI model catalog on every invocation.
    """
    explicit_model = model_override.strip() or inference_model.strip()
    model = explicit_model or configured_model(config, fallback=fallback_model)
    explicit_provider = provider_override.strip()
    if explicit_provider:
        return model, explicit_provider
    if not explicit_model or detect_provider is None:
        return model, None

    model_config = config.get("model", {})
    configured_provider = (
        str(model_config.get("provider") or "").strip().lower()
        if isinstance(model_config, dict)
        else ""
    )
    detected = detect_provider(
        explicit_model,
        configured_provider or inference_provider.strip().lower() or "auto",
    )
    if detected:
        return detected
    return model, None
