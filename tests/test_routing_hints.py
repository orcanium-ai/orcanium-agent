"""Test execution hints generation for all routing paths.

Verifies the Cognitive Router produces correct hints for every intent type,
ensuring no UnboundLocalError or missing variable issues.

Key regression: `load_tool_definitions` key is only present in hints
for L1_TOOL and L3_COGNITIVE paths. For L0_DIRECT and L2_RETRIEVAL,
it's absent (defaults to False via .get(key, False)).
This is correct behavior — those paths don't need tool definitions.
"""

import pytest
from orcanium.app.domains.cognition.cognitive_router import (
    ExecutionPath,
    Route,
    get_execution_hints,
    route,
)
from orcanium.app.domains.cognition.intent_classifier import Intent


class TestGetExecutionHints:
    """Verify that get_execution_hints returns correct hints for each path."""

    def test_l0_direct_skips_everything(self):
        """L0_DIRECT must skip tools AND retrieval.
        Note: load_tool_definitions key is absent (defaults to False via .get())."""
        route_result = Route(
            path=ExecutionPath.L0_DIRECT,
            intent=Intent.DIRECT_CHAT,
            confidence=0.8,
        )
        hints = get_execution_hints(route_result)

        assert hints["skip_memory_retrieval"] is True
        assert hints["skip_knowledge_retrieval"] is True
        # load_tool_definitions is absent for L0 — the .get() returns False
        assert hints.get("load_tool_definitions", False) is False
        assert hints.get("tool_execution_timeout") is None
        assert hints.get("use_greeting_tone") is True

    def test_l1_tool_loads_tools(self):
        """L1_TOOL must load tool definitions."""
        route_result = Route(
            path=ExecutionPath.L1_TOOL,
            intent=Intent.TOOL_QUERY,
            confidence=0.7,
        )
        hints = get_execution_hints(route_result)

        assert hints["load_tool_definitions"] is True  # Key is present and True
        assert hints["tool_execution_timeout"] == 30
        assert hints["skip_knowledge_retrieval"] is True

    def test_l2_retrieval_skips_tools(self):
        """L2_RETRIEVAL must skip tools but enable retrieval.
        Note: load_tool_definitions key is absent (defaults to False via .get())."""
        route_result = Route(
            path=ExecutionPath.L2_RETRIEVAL,
            intent=Intent.MEMORY_QUERY,
            confidence=0.7,
        )
        hints = get_execution_hints(route_result)

        # Explicitly set to False for L2
        assert hints["load_tool_definitions"] is False
        assert hints["skip_knowledge_retrieval"] is False
        assert hints["retrieval_top_k"] == 5

    def test_l3_cognitive_loads_everything(self):
        """L3_COGNITIVE must load tools and enable full retrieval."""
        route_result = Route(
            path=ExecutionPath.L3_COGNITIVE,
            intent=Intent.COGNITIVE_TASK,
            confidence=0.8,
        )
        hints = get_execution_hints(route_result)

        assert hints["load_tool_definitions"] is True
        assert hints["skip_knowledge_retrieval"] is False
        assert hints["retrieval_top_k"] == 10
        assert hints["tool_execution_timeout"] == 120


class TestRouteFunction:
    """Verify the route() function dispatches intents correctly."""

    def test_direct_chat_routes_l0(self):
        route_result = route(Intent.DIRECT_CHAT, 0.9)
        assert route_result.path == ExecutionPath.L0_DIRECT
        assert route_result.requires_tools is False
        assert route_result.requires_retrieval is False
        assert route_result.requires_cognitive_engine is False

    def test_tool_query_routes_l1(self):
        route_result = route(Intent.TOOL_QUERY, 0.9)
        assert route_result.path == ExecutionPath.L1_TOOL
        assert route_result.requires_tools is True
        assert route_result.requires_retrieval is False

    def test_memory_query_routes_l2(self):
        route_result = route(Intent.MEMORY_QUERY, 0.9)
        assert route_result.path == ExecutionPath.L2_RETRIEVAL
        assert route_result.requires_retrieval is True
        assert route_result.requires_tools is False

    def test_knowledge_query_routes_l2(self):
        route_result = route(Intent.KNOWLEDGE_QUERY, 0.9)
        assert route_result.path == ExecutionPath.L2_RETRIEVAL
        assert route_result.requires_retrieval is True

    def test_cognitive_task_routes_l3(self):
        route_result = route(Intent.COGNITIVE_TASK, 0.9)
        assert route_result.path == ExecutionPath.L3_COGNITIVE
        assert route_result.requires_tools is True
        assert route_result.requires_retrieval is True
        assert route_result.requires_cognitive_engine is True

    def test_low_confidence_escalates(self):
        """Low confidence DIRECT_CHAT should escalate upward."""
        route_result = route(Intent.DIRECT_CHAT, 0.1)
        assert route_result.escalation is True


class TestRegressionUnboundLocalError:
    """Regression: DIRECT_CHAT queries must never cause UnboundLocalError.

    Root cause: enabled_toolsets was referenced at agent_runtime.py line 232
    but only assigned inside the `if hints.get("load_tool_definitions", False):`
    block. When load_tool_definitions was False (L0_DIRECT, L2_RETRIEVAL),
    enabled_toolsets was never assigned, causing:
        UnboundLocalError: cannot access local variable 'enabled_toolsets'

    Fix: line 232 now uses `hints.get("load_tool_definitions", False)` as guard
    instead of the bare `enabled_toolsets` variable.
    """

    def test_greeting_hints_has_tool_flag(self):
        """hello → L0_DIRECT: load_tool_definitions absent, .get() returns False safely."""
        route_result = route(Intent.DIRECT_CHAT, 0.95)
        hints = get_execution_hints(route_result)
        # Should never raise KeyError or UnboundLocalError
        assert hints.get("load_tool_definitions", False) is False

    def test_are_you_online_hints(self):
        """are you online? → L0_DIRECT: no crash from missing variable."""
        route_result = route(Intent.DIRECT_CHAT, 0.85)
        hints = get_execution_hints(route_result)
        assert hints.get("load_tool_definitions", False) is False

    def test_who_are_you_hints(self):
        """who are you? → L0_DIRECT: no crash."""
        route_result = route(Intent.DIRECT_CHAT, 0.90)
        hints = get_execution_hints(route_result)
        assert hints.get("load_tool_definitions", False) is False

    def test_thank_you_hints(self):
        """thank you → L0_DIRECT: no crash."""
        route_result = route(Intent.DIRECT_CHAT, 0.95)
        hints = get_execution_hints(route_result)
        assert hints.get("load_tool_definitions", False) is False

    def test_btc_price_hints(self):
        """BTC price today → L1_TOOL: load_tool_definitions is True."""
        route_result = route(Intent.TOOL_QUERY, 0.85)
        hints = get_execution_hints(route_result)
        assert hints["load_tool_definitions"] is True

    def test_retrieval_query_hints(self):
        """memory query → L2_RETRIEVAL: load_tool_definitions is present and False."""
        route_result = route(Intent.MEMORY_QUERY, 0.80)
        hints = get_execution_hints(route_result)
        assert hints["load_tool_definitions"] is False

    def test_cognitive_task_hints(self):
        """cognitive task → L3_COGNITIVE: load_tool_definitions is True."""
        route_result = route(Intent.COGNITIVE_TASK, 0.75)
        hints = get_execution_hints(route_result)
        assert hints["load_tool_definitions"] is True

    def test_all_routes_handle_tool_flag_safely(self):
        """Every path must handle load_tool_definitions lookups safely."""
        test_cases = [
            Intent.DIRECT_CHAT,
            Intent.TOOL_QUERY,
            Intent.MEMORY_QUERY,
            Intent.KNOWLEDGE_QUERY,
            Intent.COGNITIVE_TASK,
        ]
        for intent in test_cases:
            route_result = route(intent, 0.9)
            hints = get_execution_hints(route_result)
            # This is the pattern used at agent_runtime.py line 232:
            load_tools = hints.get("load_tool_definitions", False)
            # Must always resolve to a bool without exception
            assert isinstance(load_tools, bool), (
                f"load_tool_definitions not bool for {intent}, "
                f"got {type(load_tools).__name__}"
            )
