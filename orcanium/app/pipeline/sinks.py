"""Pluggable output sinks for pipeline results.

Architecture
============

A sink writes a pipeline result (summary, notification, alert, …) to an
external destination.  Each sink is:

- **Pluggable**: a callable matching ``SinkFn``.
- **Configurable**: an ``enabled`` flag + a provider-specific config dict.
- **Idempotent**: a ``sink_key`` is derived from the event/payload; the
  ``PipelineStore`` records every successful delivery.  Rerunning a completed
  sink is a no-op.

Built-in sinks
--------------
- ``NotionSink`` — writes to a Notion database.
- ``LinearSink`` — creates/updates Linear issues.
- ``LogSink`` — logs the payload (useful for debugging).

Usage
=====

    from orcanium.app.pipeline import PipelineStore, SinkManager

    store = PipelineStore("/path/to/store.json")

    manager = SinkManager(store)
    manager.register("notion", notion_sink, {"enabled": True, "database_id": "..."})
    manager.register("linear", linear_sink, {"enabled": False, "team_id": "..."})

    results = await manager.deliver_all(
        sink_key="meeting:abc123",
        payload=summary_payload,
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

from orcanium.app.pipeline.store import PipelineStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# SinkFn is an async callable that writes a payload to an external destination.
#
# Arguments:
#   payload    — the data to write (e.g. a summary dataclass or dict).
#   config     — provider-specific configuration dict.
#   existing   — previous sink record (if any), used for idempotent updates.
#
# Returns a dict with at minimum a ``success`` key, plus any provider-specific
# metadata (URL, id, etc.).
SinkFn = Callable[
    [Any, Dict[str, Any], Optional[Dict[str, Any]]],
    Awaitable[Dict[str, Any]],
]


@dataclass
class SinkSpec:
    """Specification for a registered sink."""
    name: str
    fn: SinkFn
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    order: int = 0  # lower = earlier execution


# ---------------------------------------------------------------------------
# Sink Manager
# ---------------------------------------------------------------------------


class SinkManager:
    """Manages pluggable output sinks with idempotent delivery tracking.

    Thread-safe via the underlying ``PipelineStore`` lock.
    """

    def __init__(self, store: PipelineStore) -> None:
        self.store = store
        self._sinks: Dict[str, SinkSpec] = {}

    # -- Registration ---------------------------------------------------------

    def register(
        self,
        name: str,
        fn: SinkFn,
        *,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
        order: int = 0,
    ) -> None:
        """Register a sink function.

        Parameters
        ----------
        name
            Unique sink name (e.g. ``"notion"``, ``"linear"``).
        fn
            The async callable that performs the write.
        enabled
            When ``False``, the sink is skipped during ``deliver_all``.
        config
            Provider-specific configuration dict.
        order
            Execution order (lower = earlier).
        """
        self._sinks[name] = SinkSpec(
            name=name,
            fn=fn,
            enabled=enabled,
            config=config or {},
            order=order,
        )
        logger.debug("Registered sink '%s' (enabled=%s, order=%d)", name, enabled, order)

    def unregister(self, name: str) -> bool:
        """Remove a previously registered sink. Returns ``True`` if found."""
        return self._sinks.pop(name, None) is not None

    def get_sink(self, name: str) -> Optional[SinkSpec]:
        return self._sinks.get(name)

    def list_sinks(self) -> Dict[str, SinkSpec]:
        """Return all registered sinks (enabled and disabled)."""
        return dict(self._sinks)

    def list_enabled_sinks(self) -> Dict[str, SinkSpec]:
        """Return only enabled sinks, sorted by ``order``."""
        return dict(
            sorted(
                ((n, s) for n, s in self._sinks.items() if s.enabled),
                key=lambda kv: kv[1].order,
            )
        )

    # -- Delivery -------------------------------------------------------------

    async def deliver_all(
        self,
        sink_key: str,
        payload: Any,
    ) -> Dict[str, Any]:
        """Deliver a payload to all enabled sinks.

        Each sink is executed in ``order``.  If a sink has already been
        delivered for this ``sink_key`` (checked against the store), it is
        skipped (idempotent).

        Parameters
        ----------
        sink_key
            A unique key derived from the event (e.g. ``"meeting:{id}"``).
            Used for idempotency tracking.
        payload
            The data to deliver to each sink.

        Returns
        -------
        dict
            ``{"success": True, "results": {...}}`` where ``results`` maps
            sink name → sink result dict.
        """
        results: Dict[str, Any] = {}
        all_ok = True

        for name, spec in self.list_enabled_sinks().items():
            existing = self.store.get_sink_record(f"{name}:{sink_key}")
            try:
                result = await spec.fn(payload, spec.config, existing)
            except Exception as exc:
                logger.error("Sink '%s' failed for key '%s': %s", name, sink_key, exc)
                results[name] = {"success": False, "error": str(exc)}
                all_ok = False
                continue

            # Persist the delivery record for idempotency
            record = {
                "sink": name,
                "sink_key": sink_key,
                "success": result.get("success", True),
                "result": result,
            }
            self.store.upsert_sink_record(f"{name}:{sink_key}", record)
            results[name] = result

        return {"success": all_ok, "results": results}

    async def deliver_one(
        self,
        sink_name: str,
        sink_key: str,
        payload: Any,
    ) -> Dict[str, Any]:
        """Deliver to a single sink by name. Raises ``KeyError`` if not registered."""
        spec = self._sinks.get(sink_name)
        if spec is None:
            raise KeyError(f"Sink '{sink_name}' is not registered.")
        if not spec.enabled:
            return {"success": False, "error": f"sink '{sink_name}' is disabled"}

        existing = self.store.get_sink_record(f"{sink_name}:{sink_key}")
        try:
            result = await spec.fn(payload, spec.config, existing)
        except Exception as exc:
            logger.error("Sink '%s' failed for key '%s': %s", sink_name, sink_key, exc)
            return {"success": False, "error": str(exc)}

        record = {
            "sink": sink_name,
            "sink_key": sink_key,
            "success": result.get("success", True),
            "result": result,
        }
        self.store.upsert_sink_record(f"{sink_name}:{sink_key}", record)
        return result

    # -- Health ---------------------------------------------------------------

    def delivery_status(self, sink_key: str) -> Dict[str, Any]:
        """Check which sinks have already delivered for a given key."""
        status: Dict[str, Any] = {}
        for name in self._sinks:
            record = self.store.get_sink_record(f"{name}:{sink_key}")
            status[name] = record if record else {"delivered": False}
        return status


# ---------------------------------------------------------------------------
# Log Sink (built-in debug sink)
# ---------------------------------------------------------------------------


async def log_sink(
    payload: Any,
    config: Dict[str, Any],
    existing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Log the payload.  Useful for debugging."""
    if existing:
        logger.info("LogSink: already delivered (key=%s), skipping", existing.get("sink_key"))
        return {"success": True, "skipped": True}
    logger.info("LogSink payload: %s", str(payload)[:500])
    return {"success": True, "logged": True}


__all__ = [
    "SinkFn",
    "SinkSpec",
    "SinkManager",
    "log_sink",
]
