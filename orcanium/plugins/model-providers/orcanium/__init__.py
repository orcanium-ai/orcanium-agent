"""Orcanium Portal provider profile."""

from typing import Any

from agent.portal_tags import orcanium_portal_tags
from providers import register_provider
from providers.base import ProviderProfile


class OrcaniumProfile(ProviderProfile):
    """Orcanium Portal — product tags, reasoning with Orcanium-specific omission."""

    def build_extra_body(
        self, *, session_id: str | None = None, **context
    ) -> dict[str, Any]:
        return {"tags": orcanium_portal_tags()}

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        supports_reasoning: bool = False,
        **context,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Orcanium: passes full reasoning_config, but OMITS when disabled."""
        extra_body = {}
        if supports_reasoning:
            if reasoning_config is not None:
                rc = dict(reasoning_config)
                if rc.get("enabled") is False:
                    pass  # Orcanium omits reasoning when disabled
                else:
                    extra_body["reasoning"] = rc
            else:
                extra_body["reasoning"] = {"enabled": True, "effort": "medium"}
        return extra_body, {}


orcanium = OrcaniumProfile(
    name="orcanium",
    aliases=("orcanium-portal", "orcanium"),
    env_vars=("ORCANIUM_API_KEY",),
    display_name="Orcanium",
    description="Orcanium — Orcanium model family",
    signup_url="https://orcanium.com/",
    fallback_models=(
        "orcanium-3-405b",
        "orcanium-3-70b",
    ),
    base_url="https://inference.orcanium.com/v1",
    auth_type="oauth_device_code",
)

register_provider(orcanium)
