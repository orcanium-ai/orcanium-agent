"""Hook Registry — pre/post execution hooks for tool calls and events."""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

HookHandler = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]


class HookRegistry:
    """Registry for pre/post execution hooks."""

    def __init__(self):
        self._pre_tool_call: List[HookHandler] = []
        self._post_tool_call: List[HookHandler] = []
        self._pre_message: List[HookHandler] = []
        self._post_message: List[HookHandler] = []

    def register_pre_tool(self, handler: HookHandler) -> None:
        self._pre_tool_call.append(handler)

    def register_post_tool(self, handler: HookHandler) -> None:
        self._post_tool_call.append(handler)

    def register_pre_message(self, handler: HookHandler) -> None:
        self._pre_message.append(handler)

    def register_post_message(self, handler: HookHandler) -> None:
        self._post_message.append(handler)

    def run_pre_tool(self, context: Dict[str, Any]) -> Dict[str, Any]:
        for handler in self._pre_tool_call:
            try:
                result = handler(context)
                if result:
                    context.update(result)
            except Exception as e:
                logger.warning(f"Pre-tool hook failed: {e}")
        return context

    def run_post_tool(self, context: Dict[str, Any]) -> Dict[str, Any]:
        for handler in self._post_tool_call:
            try:
                result = handler(context)
                if result:
                    context.update(result)
            except Exception as e:
                logger.warning(f"Post-tool hook failed: {e}")
        return context


hook_registry = HookRegistry()
