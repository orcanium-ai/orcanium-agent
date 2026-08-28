"""ContextPlanner — deterministic planner that decides which context stores
to retrieve for a given request. No LLM. No retrieval. Only planning.

Replaces the old retrieval-all approach with conditional retrieval per request.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from orcanium.app.domains.cognition.intent_classifier import Intent


@dataclass
class ContextPlan:
    """Deterministic plan specifying which stores to retrieve."""

    retrieve_memory: bool = False
    retrieve_knowledge: bool = False
    retrieve_skills: bool = False
    retrieve_state: bool = False
    needs_tools: bool = False
    needs_working_memory: bool = True
    top_k: int = 5
    reasoning: str = ""


class ContextPlanner:
    """Deterministic planner — decides which stores are needed.

    Uses only:
        - Classified intent
        - Confidence score
        - Matched pattern labels
        - Execution path requirements

    Never calls an LLM. Never retrieves data.
    """

    @staticmethod
    def plan(
        intent: Intent,
        confidence: float,
        matched_patterns: Optional[List[str]] = None,
    ) -> ContextPlan:
        """Create a retrieval plan based on intent and matched patterns."""
        patterns = set(matched_patterns or [])

        # DIRECT_CHAT — no retrieval needed
        if intent == Intent.DIRECT_CHAT:
            return ContextPlan(
                needs_working_memory=False,
                reasoning="Direct chat — no retrieval needed",
            )

        # Check pattern-specific plans first (most specific)
        if "crypto_price" in patterns or "coingecko" in patterns:
            return ContextPlan(
                retrieve_skills=True,
                needs_tools=True,
                needs_working_memory=False,
                top_k=3,
                reasoning="Tool query — only skills needed for tool lookup",
            )

        if "summarize" in patterns or "remind" in patterns or "recap" in patterns:
            return ContextPlan(
                retrieve_memory=True,
                retrieve_state=True,
                top_k=10,
                reasoning="Memory/state recall — no knowledge or skills needed",
            )

        if "compare_products" in patterns or "feature_comparison" in patterns:
            return ContextPlan(
                retrieve_knowledge=True,
                retrieve_state=True,
                top_k=10,
                reasoning="Comparison — needs knowledge and current state",
            )

        if "continue_task" in patterns or "resume" in patterns:
            return ContextPlan(
                retrieve_state=True,
                retrieve_memory=True,
                top_k=5,
                reasoning="Task continuation — needs state and recent memory",
            )

        if "system_design" in patterns or "architecture" in patterns:
            return ContextPlan(
                retrieve_memory=True,
                retrieve_knowledge=True,
                retrieve_skills=True,
                retrieve_state=True,
                needs_tools=True,
                top_k=10,
                reasoning="Architecture design — full context needed",
            )

        # Intent-based defaults
        if intent == Intent.KNOWLEDGE_QUERY:
            return ContextPlan(
                retrieve_knowledge=True,
                reasoning="Knowledge query — only knowledge store needed",
            )

        if intent == Intent.MEMORY_QUERY:
            return ContextPlan(
                retrieve_memory=True,
                retrieve_state=True,
                top_k=8,
                reasoning="Memory query — memory and state needed",
            )

        if intent == Intent.TOOL_QUERY:
            return ContextPlan(
                retrieve_skills=True,
                needs_tools=True,
                top_k=5,
                reasoning="Tool query — skills and tools needed",
            )

        if intent == Intent.COGNITIVE_TASK:
            return ContextPlan(
                retrieve_memory=True,
                retrieve_knowledge=True,
                retrieve_skills=True,
                retrieve_state=True,
                needs_tools=True,
                top_k=10,
                reasoning="Cognitive task — full context with tools",
            )

        # Default fallback — minimal retrieval
        return ContextPlan(
            retrieve_memory=True,
            top_k=5,
            reasoning="Default fallback — recent memory only",
        )
