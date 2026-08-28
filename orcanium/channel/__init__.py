"""Gateway — multi-platform messaging integration for Orcanium.

Provides a unified channel connecting the Orcanium agent to messaging
platforms (Telegram, WhatsApp, Slack, Signal, and more) with:
- Session management (persistent conversations with reset policies)
- Dynamic context injection (agent knows where messages come from)
- Delivery routing (scheduled task outputs to appropriate channels)
- Platform-specific streaming (progressive message editing, typing indicators)
"""

from orcanium.channel.config import GatewayConfig, PlatformConfig, HomeChannel, load_gateway_config
from orcanium.channel.session import (
    SessionContext,
    SessionStore,
    SessionResetPolicy,
    build_session_context_prompt,
)
from orcanium.channel.delivery import DeliveryRouter, DeliveryTarget

__all__ = [
    # Config
    "GatewayConfig",
    "PlatformConfig",
    "HomeChannel",
    "load_gateway_config",
    # Session
    "SessionContext",
    "SessionStore",
    "SessionResetPolicy",
    "build_session_context_prompt",
    # Delivery
    "DeliveryRouter",
    "DeliveryTarget",
]
