"""Bridge — adapts reference-agent streaming to Orcanium's adapter lifecycle.

Reference-agent adapters are async and expect GatewayRunner to manage
their lifecycle. Orcanium runs a sync FastAPI app with thread-based
adapters. This bridge uses Orcanium's proven adapter pattern for
connections while leveraging the reference-agent's streaming infrastructure
(stream_consumer, stream_events, display_config).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Orcanium's own adapter classes (sync, thread-based, proven working)
_PLATFORM_ADAPTERS = {}


def _load_adapter_map():
    """Lazy-load adapter classes from Orcanium's app domain."""
    global _PLATFORM_ADAPTERS
    if _PLATFORM_ADAPTERS:
        return
    try:
        from orcanium.app.domains.channel.platforms.telegram import TelegramAdapter
        _PLATFORM_ADAPTERS = {
            "telegram": TelegramAdapter,
        }
    except ImportError as e:
        logger.warning(f"Gateway: adapter imports failed: {e}")


class ChannelRunner:
    """Gateway runner using Orcanium's proven sync adapter pattern."""

    def __init__(self):
        self._running = False
        self._adapters: Dict[str, Any] = {}

    def start_all(self) -> None:
        _load_adapter_map()
        from orcanium.app.core.db import GatewayChannel, SessionLocal
        db = SessionLocal()
        try:
            channels = db.query(GatewayChannel).filter(GatewayChannel.enabled == True).all()
            for chan in channels:
                self._start_adapter(chan.id, chan.platform, chan.get_config() or {})
            logger.info(f"ChannelRunner: started {len(channels)} channel(s)")
        except Exception as e:
            logger.error(f"ChannelRunner: start_all failed: {e}")
        finally:
            db.close()
        self._running = True

    def stop_all(self) -> None:
        for channel_id, adapter in list(self._adapters.items()):
            try:
                adapter.stop()
            except Exception as e:
                logger.warning(f"ChannelRunner: stop error for {channel_id}: {e}")
        self._adapters.clear()
        self._running = False
        logger.info("ChannelRunner: stopped")

    def reload_channel(self, channel_id: str, platform: str,
                       config: Dict[str, Any], enabled: bool) -> None:
        self.stop_channel(channel_id)
        if enabled:
            self._start_adapter(channel_id, platform, config)

    def stop_channel(self, channel_id: str) -> None:
        adapter = self._adapters.pop(channel_id, None)
        if adapter:
            try:
                adapter.stop()
                logger.info(f"ChannelRunner: stopped channel {channel_id}")
            except Exception as e:
                logger.warning(f"ChannelRunner: stop_channel {channel_id} error: {e}")

    def is_running(self) -> bool:
        return self._running

    def get_adapter(self, channel_id: str) -> Optional[Any]:
        """Get a specific adapter by channel_id, or ``None``."""
        return self._adapters.get(channel_id)

    def get_running_adapters(self) -> List[Any]:
        return [a for a in self._adapters.values() if getattr(a, '_running', False)]

    def _start_adapter(self, channel_id: str, platform: str,
                       config: Dict[str, Any]) -> None:
        _load_adapter_map()
        adapter_class = _PLATFORM_ADAPTERS.get(platform)
        if not adapter_class:
            logger.warning(f"ChannelRunner: no adapter for '{platform}' ({channel_id})")
            return
        try:
            adapter = adapter_class(channel_id=channel_id, config=config)
            adapter.start()
            self._adapters[channel_id] = adapter
            logger.info(f"ChannelRunner: started {platform} channel {channel_id}")
        except Exception as e:
            logger.error(f"ChannelRunner: failed to start {platform} channel {channel_id}: {e}")


channel_runner = ChannelRunner()
