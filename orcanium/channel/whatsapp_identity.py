"""Stub — WhatsApp identity management (not needed in Orcanium).

Provides the imports that channel.session.py and authz_mixin.py expect
without actual WhatsApp identity resolution logic.
"""


def canonical_whatsapp_identifier(identifier: str) -> str:
    """Stub — returns the identifier unchanged."""
    return identifier


def normalize_whatsapp_identifier(identifier: str) -> str:
    """Stub — returns the identifier unchanged."""
    return identifier


def expand_whatsapp_aliases(identifier: str) -> list:
    """Stub — returns the identifier as a single-element list."""
    return [identifier]


WhatsAppIdentity = None
WhatsAppIdentityStore = None
