"""Orcanium Pipeline — general-purpose durable pipeline orchestration.

Architecture
============

A pipeline is a state machine that runs a sequence of stages. Each stage
transitions the pipeline's status through an explicit lifecycle. The pipeline
store provides durable JSON-backed persistence so pipelines survive restarts.

State model
-----------
    received → stage_1 → stage_2 → ... → stage_N → completed
                                                      ↓
                                                 failed / retry_scheduled

    ACTIVE_PIPELINE_STATES: intermediate status values.
    TERMINAL_PIPELINE_STATES: completed | failed | retry_scheduled | cancelled

Deduplication
-------------
Each event/notification that triggers a pipeline run is hashed (SHA-256 of
the canonical JSON body, or the explicit ``id`` field). If the same receipt
key is seen again the pipeline is skipped — ensuring idempotent execution.

Retry model
-----------
- ``PipelineRetryableError`` → status ``retry_scheduled`` (transient failure).
- Any other exception → status ``failed`` with error_info dict.
- External schedulers (cron, backoff) consume the ``retry_scheduled`` state.

Sinks
-----
Output writers (Notion, Linear, Teams, etc.) are pluggable ``SinkFn``
callables. Each sink has an ``enabled`` flag and an idempotent record
(``sink_records``) that prevents double-delivery.

Gateway Runtime Binding
-----------------------
The ``RuntimeBinder`` attaches a pipeline runtime to a gateway adapter via
a ``NotificationScheduler`` callback.  If the runtime is unavailable, a
drop-scheduler is installed so webhook queues don't back up.
"""

from __future__ import annotations

from orcanium.app.agent.pipeline_types import (
    # State constants
    TERMINAL_PIPELINE_STATES,
    ACTIVE_PIPELINE_STATES,
    DEFAULT_ACTIVE_PIPELINE_STATES,
    # Exception hierarchy
    PipelineError,
    PipelineRetryableError,
    PipelineSinkError,
    # Enums
    PipelineStage,
    PipelineStatus,
    ExecutionMode,
    # Dataclasses
    StageResult,
    PipelineResult,
)

from orcanium.app.pipeline.store import (
    PipelineStore,
    resolve_pipeline_store_path,
)

from orcanium.app.pipeline.subscriptions import (
    SubscriptionProvider,
    SubscriptionManager,
)

from orcanium.app.pipeline.runtime import (
    NotificationScheduler,
    RuntimeBinder,
    resolve_config_value,
    resolve_config_path,
)

from orcanium.app.pipeline.sinks import (
    SinkFn,
    SinkSpec,
    SinkManager,
    log_sink,
)

__all__ = [
    # From store
    "PipelineStore",
    "resolve_pipeline_store_path",
    # From subscriptions
    "SubscriptionProvider",
    "SubscriptionManager",
    # From runtime
    "NotificationScheduler",
    "RuntimeBinder",
    "resolve_config_value",
    "resolve_config_path",
    # From sinks
    "SinkFn",
    "SinkSpec",
    "SinkManager",
    "log_sink",
    # From pipeline_types
    "TERMINAL_PIPELINE_STATES",
    "ACTIVE_PIPELINE_STATES",
    "DEFAULT_ACTIVE_PIPELINE_STATES",
    "PipelineError",
    "PipelineRetryableError",
    "PipelineSinkError",
    "PipelineStage",
    "PipelineStatus",
    "ExecutionMode",
    "StageResult",
    "PipelineResult",
]
