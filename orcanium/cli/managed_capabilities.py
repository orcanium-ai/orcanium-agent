"""Compatibility surface for managed Gateway capability discovery.

There is no local subscription state. The name remains only because local tool
configuration imports this module; all answers come from the Gateway API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from orcanium.cli.managed_identity import get_managed_gateway_identity


MANAGED_FEATURE_COVERAGE_CATEGORY = {
    "web": "web",
    "image_gen": "image_generation",
    "video_gen": "video_generation",
    "tts": "text_to_speech",
    "stt": "speech_to_text",
    "browser": "advanced_browser",
    "modal": "remote_execution",
}


@dataclass(frozen=True)
class ManagedFeature:
    key: str
    label: str
    available: bool
    active: bool = False
    managed_by_orcanium: bool = False
    included_by_default: bool = False
    current_provider: str | None = None


class ManagedCapabilities:
    def __init__(self) -> None:
        account = get_managed_gateway_identity()
        self.account_info = account
        self.orcanium_auth_present = account.logged_in
        self.tool_gateway_enabled = account.tool_gateway_entitled
        self._features = tuple(
            ManagedFeature(
                key=key,
                label=key.replace("_", " ").title(),
                available=capability in account.enabled_capabilities,
                managed_by_orcanium=capability in account.enabled_capabilities,
            )
            for key, capability in MANAGED_FEATURE_COVERAGE_CATEGORY.items()
        )
        self.features = {feature.key: feature for feature in self._features}
        for feature in self._features:
            setattr(self, feature.key, feature)
        self.tool_gateway = self

    def items(self) -> Iterator[ManagedFeature]:
        return iter(self._features)


def get_managed_capabilities(config=None, force_fresh: bool = False) -> ManagedCapabilities:
    del config, force_fresh
    return ManagedCapabilities()


def prompt_enable_tool_gateway(agent_name, config):
    del agent_name, config
    return get_managed_capabilities().tool_gateway_enabled


def apply_orcanium_managed_defaults(config, enabled_toolsets=None, force_fresh=False):
    del enabled_toolsets, force_fresh
    return config if isinstance(config, dict) else {}
