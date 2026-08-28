"""Runtime binding — dynamically attach pipeline runtimes to gateway adapters.

Provides the ``RuntimeBinder`` and ``NotificationScheduler`` protocol that
decouple pipeline logic from channel adapter lifecycle.

Architecture
============

A gateway adapter receives external events (webhooks, messages, platform
notifications). The ``RuntimeBinder`` dynamically attaches a scheduler
callback so events are routed to a pipeline runtime for processing:

    Adapter.on_event → scheduler(event) → pipeline.run(event)

If the pipeline runtime is unavailable (misconfiguration, missing credentials,
transient error) the binder installs a *drop-scheduler* that silently
acknowledges the event without processing — preventing webhook queues from
backing up while the configuration is fixed.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# NotificationScheduler is an async callback that a gateway adapter calls
# when it receives an incoming notification. The callback routes the
# notification to the appropriate pipeline runtime.
NotificationScheduler = Callable[[Dict[str, Any], Any], Awaitable[None]]

# DropScheduler is a fallback scheduler that silently drops notifications
# when the pipeline runtime is unavailable.
async def _drop_scheduler(notification: Dict[str, Any], event: Any) -> None:
    logger.debug(
        "Dropping notification because runtime is unavailable: "
        "id=%s resource=%s",
        notification.get("id"),
        notification.get("resource"),
    )


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def resolve_config_value(
    key: str,
    *,
    env_var: str = "",
    config_section: Optional[Dict[str, Any]] = None,
    default: Any = None,
) -> Any:
    """Resolve a config value with env-override.

    Order:
      1. ``config_section[key]`` (if provided and non-None).
      2. ``os.environ[env_var]`` (if ``env_var`` is set and non-empty).
      3. ``default``.
    """
    if config_section is not None:
        value = config_section.get(key)
        if value is not None:
            return value
    if env_var:
        env_value = os.environ.get(env_var)
        if env_value is not None:
            stripped = env_value.strip()
            if stripped:
                return stripped
    return default


def resolve_config_path(
    key: str,
    *,
    env_var: str = "",
    config_section: Optional[Dict[str, Any]] = None,
    default: Optional[str] = None,
) -> Optional[Path]:
    """Resolve a filesystem path from config with env-override."""
    value = resolve_config_value(
        key, env_var=env_var, config_section=config_section, default=default
    )
    if value is None:
        return None
    return Path(str(value))


# ---------------------------------------------------------------------------
# Runtime Binder
# ---------------------------------------------------------------------------


class RuntimeBinder:
    """Generic runtime binder that attaches pipeline runtimes to gateway adapters.

    Usage::

        binder = RuntimeBinder()
        ok = await binder.bind(
            adapter=channel.adapters["msgraph_webhook"],
            runtime=my_pipeline,
            runtime_label="teams_pipeline",
            scheduler=pipeline.run_notification,
        )
        if not ok:
            logger.warning("Runtime unavailable; notifications will be dropped.")
    """

    def __init__(self) -> None:
        self._attached: Dict[str, Any] = {}

    @property
    def attached_runtimes(self) -> Dict[str, Any]:
        return dict(self._attached)

    async def bind(
        self,
        *,
        adapter: Any,
        runtime: Any,
        runtime_label: str = "pipeline",
        scheduler: Optional[NotificationScheduler] = None,
    ) -> bool:
        """Bind a pipeline runtime to a gateway adapter.

        Parameters
        ----------
        adapter
            A gateway adapter object that has a ``set_notification_scheduler``
            method, or an ``on_event`` attribute / property.
        runtime
            The pipeline runtime object (e.g. ``TeamsMeetingPipeline``).
        runtime_label
            Human-readable label for log messages.
        scheduler
            The async callback to invoke when a notification arrives.
            Defaults to ``runtime.run_notification`` if the runtime has one.

        Returns
        -------
        bool
            ``True`` if the runtime was successfully bound.
            ``False`` if binding failed; a drop-scheduler is installed.
        """
        # Resolve scheduler from runtime if not provided
        actual_scheduler = scheduler
        if actual_scheduler is None:
            actual_scheduler = getattr(runtime, "run_notification", None)

        if actual_scheduler is None:
            # No scheduler available — install drop-scheduler
            logger.warning(
                "%s runtime has no run_notification method and no scheduler "
                "was provided. Installing drop-scheduler.",
                runtime_label,
            )
            self._install_drop_scheduler(adapter)
            return False

        # Try setting the scheduler on the adapter
        set_method = getattr(adapter, "set_notification_scheduler", None)
        if set_method is not None:
            set_method(actual_scheduler)
            self._attached[runtime_label] = runtime
            logger.info(
                "Bound %s runtime to adapter via set_notification_scheduler",
                runtime_label,
            )
            return True

        # Fall back to setting on_event attribute
        if hasattr(adapter, "on_event"):
            adapter.on_event = actual_scheduler
            self._attached[runtime_label] = runtime
            logger.info("Bound %s runtime to adapter via on_event", runtime_label)
            return True

        logger.warning(
            "Adapter has no set_notification_scheduler or on_event. "
            "Cannot bind %s runtime.",
            runtime_label,
        )
        return False

    def unbind(self, runtime_label: str) -> None:
        """Remove a previously bound runtime."""
        self._attached.pop(runtime_label, None)

    def unbind_all(self) -> None:
        """Remove all bound runtimes."""
        self._attached.clear()

    @staticmethod
    def _install_drop_scheduler(adapter: Any) -> None:
        """Install a silent drop-scheduler on the adapter."""
        set_method = getattr(adapter, "set_notification_scheduler", None)
        if set_method is not None:
            set_method(_drop_scheduler)
            logger.debug("Installed drop-scheduler on adapter")
        elif hasattr(adapter, "on_event"):
            adapter.on_event = _drop_scheduler
            logger.debug("Installed drop-scheduler on adapter.on_event")
        else:
            logger.debug(
                "Cannot install drop-scheduler: adapter has no "
                "set_notification_scheduler or on_event"
            )


__all__ = [
    "NotificationScheduler",
    "RuntimeBinder",
    "resolve_config_value",
    "resolve_config_path",
]
