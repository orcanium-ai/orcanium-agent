"""Durable JSON-backed pipeline store — thread-safe, atomic writes.

Inspired by ``TeamsPipelineStore`` in ``plugins/teams_pipeline/store.py``.
Generalised so any Orcanium pipeline (conversation, knowledge, Teams, …) can
opt into durable state without coupling to a specific plugin.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_PIPELINE_STORE_FILENAME = "pipeline_store.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_pipeline_store_path(
    path: str | Path | None = None,
    *,
    env_var: str = "ORCANIUM_PIPELINE_STORE_PATH",
    default_filename: str = DEFAULT_PIPELINE_STORE_FILENAME,
    home_resolver=None,
) -> Path:
    """Resolve pipeline store path with env-override.

    Order:
      1. Explicit ``path`` argument.
      2. ``<env_var>`` environment variable.
      3. ``home_resolver() / default_filename`` (defaults to CWD).
    """
    if path is not None:
        explicit = str(path).strip()
        if explicit:
            return Path(explicit)

    env_path = os.getenv(env_var, "").strip()
    if env_path:
        return Path(env_path)

    if home_resolver is not None:
        base = home_resolver()
    else:
        base = Path.cwd()
    return Path(base) / default_filename


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class PipelineStore:
    """JSON-backed durable store for pipeline state.

    Thread-safe via ``threading.RLock``.  Writes are atomic (write to temp
    file, then ``Path.replace``) so a crash in the middle of a write never
    corrupts the store.

    Store schema (all values are ``dict[str, dict]``):

        subscriptions        — webhook / event subscription records
        notification_receipts — deduplication receipts (SHA-256 of event body)
        event_timestamps     — arbitrary key → ISO-8601 timestamp
        jobs                 — pipeline job records
        sink_records         — idempotent output-sink delivery records
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._state: Dict[str, Dict[str, Any]] = {
            "subscriptions": {},
            "notification_receipts": {},
            "event_timestamps": {},
            "jobs": {},
            "sink_records": {},
        }
        self._load()

    # -- Persistence ---------------------------------------------------------

    def _load(self) -> None:
        with self._lock:
            if not self.path.exists():
                return
            data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
            if not isinstance(data, dict):
                return
            for key in self._state:
                self._state[key] = dict(data.get(key) or {})

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(self.path.parent),
            delete=False,
        ) as tmp:
            json.dump(self._state, tmp, indent=2, sort_keys=True)
            tmp.flush()
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.path)

    # -- Stats ---------------------------------------------------------------

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "subscriptions": len(self._state["subscriptions"]),
                "notification_receipts": len(self._state["notification_receipts"]),
                "event_timestamps": len(self._state["event_timestamps"]),
                "jobs": len(self._state["jobs"]),
                "sink_records": len(self._state["sink_records"]),
            }

    # -- Subscriptions -------------------------------------------------------

    def list_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._state["subscriptions"])

    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._state["subscriptions"].get(subscription_id)
            return deepcopy(record) if isinstance(record, dict) else None

    def upsert_subscription(
        self, subscription_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self._lock:
            existing = self._state["subscriptions"].get(subscription_id, {})
            merged = {**existing, **deepcopy(payload)}
            merged["subscription_id"] = subscription_id
            merged.setdefault("created_at", existing.get("created_at") or _utc_now_iso())
            merged["updated_at"] = _utc_now_iso()
            self._state["subscriptions"][subscription_id] = merged
            self._persist()
            return deepcopy(merged)

    def delete_subscription(self, subscription_id: str) -> bool:
        with self._lock:
            removed = self._state["subscriptions"].pop(subscription_id, None)
            if removed is None:
                return False
            self._persist()
            return True

    # -- Notification Receipts (Deduplication) --------------------------------

    @classmethod
    def build_notification_receipt_key(cls, notification: Dict[str, Any]) -> str:
        """Build a deterministic deduplication key from a notification payload.

        Uses the explicit ``id`` field when present (fast path), otherwise
        falls back to SHA-256 of the canonical JSON-sorted body.
        """
        explicit_id = notification.get("id")
        if explicit_id:
            return f"id:{explicit_id}"
        canonical = json.dumps(notification, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def has_notification_receipt(self, receipt_key: str) -> bool:
        with self._lock:
            return receipt_key in self._state["notification_receipts"]

    def record_notification_receipt(
        self,
        receipt_key: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        received_at: Optional[str] = None,
    ) -> bool:
        """Record a notification receipt.  Returns ``True`` if new, ``False``
        if already present (idempotent)."""
        with self._lock:
            if receipt_key in self._state["notification_receipts"]:
                return False
            self._state["notification_receipts"][receipt_key] = {
                "received_at": received_at or _utc_now_iso(),
                "payload": deepcopy(payload) if isinstance(payload, dict) else payload,
            }
            self._persist()
            return True

    def list_notification_receipts(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._state["notification_receipts"])

    # -- Event Timestamps ----------------------------------------------------

    def record_event_timestamp(
        self, event_key: str, timestamp: Optional[str] = None
    ) -> str:
        with self._lock:
            value = timestamp or _utc_now_iso()
            self._state["event_timestamps"][event_key] = value
            self._persist()
            return value

    def get_event_timestamp(self, event_key: str) -> Optional[str]:
        with self._lock:
            value = self._state["event_timestamps"].get(event_key)
            return str(value) if value is not None else None

    def list_event_timestamps(self) -> Dict[str, str]:
        with self._lock:
            return deepcopy(self._state["event_timestamps"])

    # -- Pipeline Jobs -------------------------------------------------------

    def upsert_job(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            existing = self._state["jobs"].get(job_id, {})
            merged = {**existing, **deepcopy(payload)}
            merged["job_id"] = job_id
            merged.setdefault("created_at", existing.get("created_at") or _utc_now_iso())
            merged["updated_at"] = _utc_now_iso()
            self._state["jobs"][job_id] = merged
            self._persist()
            return deepcopy(merged)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._state["jobs"].get(job_id)
            return deepcopy(record) if isinstance(record, dict) else None

    def list_jobs(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._state["jobs"])

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            removed = self._state["jobs"].pop(job_id, None)
            if removed is None:
                return False
            self._persist()
            return True

    # -- Sink Records (idempotent output delivery) ---------------------------

    def upsert_sink_record(
        self, sink_key: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self._lock:
            existing = self._state["sink_records"].get(sink_key, {})
            merged = {**existing, **deepcopy(payload)}
            merged["sink_key"] = sink_key
            merged.setdefault("created_at", existing.get("created_at") or _utc_now_iso())
            merged["updated_at"] = _utc_now_iso()
            self._state["sink_records"][sink_key] = merged
            self._persist()
            return deepcopy(merged)

    def get_sink_record(self, sink_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._state["sink_records"].get(sink_key)
            return deepcopy(record) if isinstance(record, dict) else None

    def list_sink_records(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._state["sink_records"])

    # -- Bulk operations -----------------------------------------------------

    def clear(self) -> None:
        """Clear all state (destructive — use with care)."""
        with self._lock:
            for key in self._state:
                self._state[key] = {}
            self._persist()

    def export_state(self) -> Dict[str, Dict[str, Any]]:
        """Return a deep copy of the full store state."""
        with self._lock:
            return deepcopy(self._state)

    def import_state(self, state: Dict[str, Dict[str, Any]]) -> None:
        """Replace full store state from a prior export."""
        with self._lock:
            for key in self._state:
                self._state[key] = deepcopy(dict(state.get(key) or {}))
            self._persist()
