"""Subscription manager — generic webhook/event subscription lifecycle.

Provides a ``SubscriptionManager`` that:
  1. Polls a remote provider (Graph API, generic webhook, …) for subscriptions.
  2. Syncs each subscription to the local ``PipelineStore``.
  3. Auto-renews expiring subscriptions within a configurable threshold.
  4. Detects orphaned local subscriptions (present in store, gone from remote).
  5. Returns a detailed report for observability.

Usage
=====

    from orcanium.app.pipeline import PipelineStore, SubscriptionManager

    class MyProvider(SubscriptionProvider):
        async def list_subscriptions(self) -> list[dict]:
            ...
        async def renew_subscription(self, sub_id: str, new_expiry: str) -> dict:
            ...

    store = PipelineStore("/path/to/store.json")
    mgr = SubscriptionManager(provider=MyProvider(), store=store)

    report = await mgr.maintain(
        renew_within_hours=24,
        extend_hours=48,
    )
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol

from orcanium.app.pipeline.store import PipelineStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


class SubscriptionProvider(ABC):
    """Abstract interface for a remote subscription backend.

    Implementations wrap specific APIs (Microsoft Graph, generic webhook,
    custom provider, …).
    """

    @abstractmethod
    async def list_subscriptions(self) -> List[Dict[str, Any]]:
        """Fetch all subscriptions from the remote provider.

        Returns a list of dicts. Each dict should contain at minimum:

            id / subscription_id : str
            expirationDateTime / expiration_datetime : str (ISO-8601)
            resource : str
            changeType / change_type : str (optional)
            notificationUrl / notification_url : str (optional)
            clientState / client_state : str (optional)

        Implementations should paginate internally and return the full list.
        """
        ...

    @abstractmethod
    async def renew_subscription(
        self, subscription_id: str, new_expiration: str
    ) -> Optional[Dict[str, Any]]:
        """Extend the expiration of a subscription.

        ``new_expiration`` is an ISO-8601 datetime string.

        Returns the updated subscription payload from the provider, or
        ``None`` if the renewal failed (the caller will mark the
        subscription as ``renewal_failed``).
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable provider name (default: class name)."""
        return type(self).__name__


# ---------------------------------------------------------------------------
# Subscription manager
# ---------------------------------------------------------------------------


class SubscriptionManager:
    """Manages the lifecycle of remote subscriptions.

    Designed to run periodically (cron, background loop).  Each cycle:

    1. Lists remote subscriptions via the provider.
    2. Syncs each managed subscription to the local store.
    3. Identifies subscriptions approaching expiry and renews them.
    4. Flags local subscriptions missing from the remote as ``missing_remote``.
    """

    def __init__(
        self,
        *,
        provider: SubscriptionProvider,
        store: PipelineStore,
        client_state_env_var: str = "",
    ) -> None:
        self.provider = provider
        self.store = store
        self._client_state_env_var = client_state_env_var

    # -- Client state ---------------------------------------------------------

    def expected_client_state(self, raw: str | None = None) -> str | None:
        """Resolve the expected ``client_state`` value.

        Order: explicit argument → environment variable → ``None``.
        """
        if raw is not None:
            value = str(raw).strip()
            if value:
                return value
        if self._client_state_env_var:
            from os import getenv

            value = getenv(self._client_state_env_var, "").strip()
            if value:
                return value
        return None

    def is_managed_subscription(
        self,
        subscription_payload: Dict[str, Any],
        *,
        expected_client_state_value: str | None,
    ) -> bool:
        """Check whether a subscription is managed by this pipeline.

        A subscription is considered "managed" if either:

        1. Its ``id`` / ``subscription_id`` exists in the local store.
        2. Its ``client_state`` / ``clientState`` matches the expected value.
        """
        subscription_id = str(
            subscription_payload.get("subscription_id")
            or subscription_payload.get("id")
            or ""
        ).strip()
        if subscription_id and self.store.get_subscription(subscription_id):
            return True

        if expected_client_state_value:
            candidate_state = str(
                subscription_payload.get("client_state")
                or subscription_payload.get("clientState")
                or ""
            ).strip()
            if candidate_state and candidate_state == expected_client_state_value:
                return True

        return False

    # -- Sync a single subscription -------------------------------------------

    def sync_subscription_record(
        self,
        subscription_payload: Dict[str, Any],
        *,
        status: str | None = None,
        renewed: bool = False,
    ) -> Dict[str, Any]:
        """Normalise a subscription payload and persist it to the local store.

        Auto-detects ``expired`` / ``active`` status when not explicitly
        provided.
        """
        # Normalise field names to snake_case
        normalized: Dict[str, Any] = {
            "subscription_id": str(
                subscription_payload.get("subscription_id")
                or subscription_payload.get("id")
                or ""
            ).strip(),
            "resource": str(
                subscription_payload.get("resource") or ""
            ).strip(),
            "change_type": str(
                subscription_payload.get("change_type")
                or subscription_payload.get("changeType")
                or ""
            ).strip(),
            "notification_url": str(
                subscription_payload.get("notification_url")
                or subscription_payload.get("notificationUrl")
                or ""
            ).strip(),
            "expiration_datetime": subscription_payload.get("expiration_datetime")
            or subscription_payload.get("expirationDateTime"),
            "client_state": subscription_payload.get("client_state")
            or subscription_payload.get("clientState"),
        }

        expiration = _parse_datetime(normalized.get("expiration_datetime"))
        effective_status = status
        if effective_status is None:
            effective_status = (
                "expired" if expiration and expiration <= _utc_now() else "active"
            )
        normalized["status"] = effective_status
        if renewed:
            normalized["latest_renewal_at"] = _utc_now_iso()

        return self.store.upsert_subscription(
            normalized["subscription_id"], normalized
        )

    # -- Maintenance cycle ----------------------------------------------------

    async def maintain(
        self,
        *,
        renew_within_hours: int = 24,
        extend_hours: int = 24,
        dry_run: bool = False,
        client_state: str | None = None,
    ) -> Dict[str, Any]:
        """Run a full subscription maintenance cycle.

        Parameters
        ----------
        renew_within_hours : int
            Renew subscriptions whose remaining lifetime is below this threshold.
        extend_hours : int
            Number of hours to extend each renewed subscription.
        dry_run : bool
            When ``True``, identify candidates but do not perform renewals.
        client_state : str, optional
            Override the expected ``client_state`` value.

        Returns
        -------
        dict
            A detailed report including counts of synced, renewed, skipped,
            and expired subscriptions, plus a list of candidates and renewed
            entries for observability.
        """
        threshold_hours = max(1, int(renew_within_hours))
        extend_hours = max(1, int(extend_hours))
        managed_client_state = self.expected_client_state(client_state)
        now = _utc_now()

        remote_subscriptions = await self.provider.list_subscriptions()
        remote_ids: set[str] = set()
        synced = 0
        renewed: List[Dict[str, Any]] = []
        candidates: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []

        for raw in remote_subscriptions:
            if not isinstance(raw, dict):
                continue
            subscription_id = str(raw.get("id") or "").strip()
            if not subscription_id:
                continue

            managed = self.is_managed_subscription(
                raw,
                expected_client_state_value=managed_client_state,
            )
            if not managed:
                skipped.append(
                    {
                        "subscription_id": subscription_id,
                        "reason": "not_managed_by_pipeline",
                    }
                )
                continue

            remote_ids.add(subscription_id)

            # Sync to local store
            try:
                self.sync_subscription_record(raw)
                synced += 1
            except Exception as exc:
                skipped.append(
                    {
                        "subscription_id": subscription_id,
                        "reason": f"failed_to_sync_local_store: {exc}",
                    }
                )
                continue

            # Check expiry
            expiration = _parse_datetime(raw.get("expirationDateTime"))
            if expiration is None:
                skipped.append(
                    {"subscription_id": subscription_id, "reason": "missing_expiration"}
                )
                continue

            seconds_until_expiry = int((expiration - now).total_seconds())

            if seconds_until_expiry < 0:
                self.store.upsert_subscription(
                    subscription_id,
                    {
                        "status": "expired",
                        "expiration_datetime": expiration.isoformat().replace(
                            "+00:00", "Z"
                        ),
                    },
                )
                skipped.append(
                    {
                        "subscription_id": subscription_id,
                        "reason": "already_expired",
                        "expiration_datetime": expiration.isoformat().replace(
                            "+00:00", "Z"
                        ),
                    }
                )
                continue

            if seconds_until_expiry > threshold_hours * 3600:
                skipped.append(
                    {
                        "subscription_id": subscription_id,
                        "reason": "not_due",
                        "expires_in_seconds": seconds_until_expiry,
                    }
                )
                continue

            # Candidate for renewal
            new_expiration = (
                max(now, expiration) + timedelta(hours=extend_hours)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            candidate = {
                "subscription_id": subscription_id,
                "resource": raw.get("resource"),
                "current_expiration": expiration.isoformat().replace("+00:00", "Z"),
                "new_expiration": new_expiration,
            }
            candidates.append(candidate)

            if dry_run:
                continue

            # Perform renewal
            try:
                result = await self.provider.renew_subscription(
                    subscription_id, new_expiration
                )
                merged = {
                    **raw,
                    **(result or {}),
                    "id": subscription_id,
                    "expirationDateTime": new_expiration,
                }
                self.sync_subscription_record(merged, status="active", renewed=True)
                renewed.append({**candidate, "result": result})
            except Exception as exc:
                self.store.upsert_subscription(
                    subscription_id,
                    {
                        "status": "renewal_failed",
                        "last_renewal_error": str(exc),
                    },
                )
                skipped.append(
                    {
                        "subscription_id": subscription_id,
                        "reason": f"renewal_failed: {exc}",
                    }
                )

        # Flag local subscriptions that no longer exist remotely
        for local_id in self.store.list_subscriptions():
            if local_id in remote_ids:
                continue
            self.store.upsert_subscription(
                local_id,
                {
                    "status": "missing_remote",
                    "last_seen_missing_remote_at": _utc_now_iso(),
                },
            )

        return {
            "success": True,
            "provider": self.provider.name,
            "dry_run": bool(dry_run),
            "store_path": str(self.store.path),
            "remote_subscription_count": len(remote_subscriptions),
            "synced_subscription_count": synced,
            "candidate_count": len(candidates),
            "renewed_count": len(renewed),
            "threshold_hours": threshold_hours,
            "extend_hours": extend_hours,
            "candidates": candidates,
            "renewed": renewed,
            "skipped": skipped,
        }

    # -- Health ----------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return a health snapshot of the subscription store."""
        subs = self.store.list_subscriptions()
        now = _utc_now()
        active = 0
        expired = 0
        missing = 0
        renewal_failed = 0
        for sub_id, payload in subs.items():
            status = str(payload.get("status") or "")
            if status == "active":
                exp = _parse_datetime(payload.get("expiration_datetime"))
                if exp and exp > now:
                    active += 1
                else:
                    expired += 1
            elif status == "expired":
                expired += 1
            elif status == "missing_remote":
                missing += 1
            elif status == "renewal_failed":
                renewal_failed += 1

        return {
            "total": len(subs),
            "active": active,
            "expired": expired,
            "missing_remote": missing,
            "renewal_failed": renewal_failed,
        }


__all__ = [
    "SubscriptionProvider",
    "SubscriptionManager",
]
