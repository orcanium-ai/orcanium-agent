"""ContextBuilder — retrieves only the stores requested by ContextPlanner.

Replaces the old unconditional retrieve_all() with conditional, targeted retrieval.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.cognition.context_planner import ContextPlan
from orcanium.app.domains.cognition.retrieval import (
    RetrievalResult,
    retrieve_knowledge,
    retrieve_memory,
    retrieve_skills,
    retrieve_state,
)


@dataclass
class ContextBundle:
    """Stores only the retrieved context needed for this request."""

    memories: List[RetrievalResult] = field(default_factory=list)
    knowledge: List[RetrievalResult] = field(default_factory=list)
    skills: List[RetrievalResult] = field(default_factory=list)
    state: List[RetrievalResult] = field(default_factory=list)

    def has_any(self) -> bool:
        return bool(self.memories or self.knowledge or self.skills or self.state)

    def __len__(self) -> int:
        return len(self.memories) + len(self.knowledge) + len(self.skills) + len(self.state)


class ContextBuilder:
    """Retrieves only the stores specified by the ContextPlan.

    Usage:
        plan = ContextPlanner.plan(intent, confidence)
        bundle = ContextBuilder.build(agent_name, query, plan)
    """

    @staticmethod
    def build(
        agent_name: str,
        query: str,
        plan: ContextPlan,
    ) -> ContextBundle:
        """Retrieve context for stores specified in the plan. Returns ContextBundle."""
        bundle = ContextBundle()

        if plan.retrieve_memory:
            bundle.memories = retrieve_memory(agent_name, query, top_k=plan.top_k)

        if plan.retrieve_knowledge:
            bundle.knowledge = retrieve_knowledge(agent_name, query, top_k=plan.top_k)

        if plan.retrieve_skills:
            bundle.skills = retrieve_skills(agent_name, query, top_k=plan.top_k)

        if plan.retrieve_state:
            bundle.state = retrieve_state(agent_name, query, top_k=plan.top_k)

        event_bus.emit_simple(
            "WORKFLOW",
            "retrieval_completed",
            agent_name,
            {
                "memories": len(bundle.memories),
                "knowledge": len(bundle.knowledge),
                "skills": len(bundle.skills),
                "state": len(bundle.state),
                "plan": plan.reasoning,
            },
        )

        return bundle
