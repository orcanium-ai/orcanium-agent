"""WorkingMemory — ephemeral cognitive workspace for the current request.

Simplified V2: contains only selected/relevant context from retrieval.
Reasoning_history and pending_actions removed (never populated at runtime).
Immutable during one request.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from orcanium.app.domains.cognition.retrieval import RetrievalResult


@dataclass
class WorkingMemory:
    """Selected context for the current request. Read-only during execution."""

    selected_memories: List[RetrievalResult] = field(default_factory=list)
    selected_knowledge: List[RetrievalResult] = field(default_factory=list)
    selected_skills: List[RetrievalResult] = field(default_factory=list)
    selected_state: List[RetrievalResult] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Format working memory into a prompt section.

        Only includes non-empty fields. Empty lists are skipped.
        """
        parts = ["## WORKING MEMORY"]

        if self.selected_memories:
            parts.append("\nRelevant Memories:")
            for item in self.selected_memories[:5]:
                parts.append(f"- [{item.category}] {item.content[:200]}")

        if self.selected_knowledge:
            parts.append("\nRelevant Knowledge:")
            for item in self.selected_knowledge[:3]:
                parts.append(f"- [{item.category}] {item.content[:200]}")

        if self.selected_skills:
            parts.append("\nRelevant Skills:")
            for item in self.selected_skills[:3]:
                parts.append(f"- {item.content[:200]}")

        if self.selected_state:
            parts.append("\nCurrent State:")
            for item in self.selected_state[:2]:
                parts.append(f"- {item.content[:200]}")

        if len(parts) == 1:
            return ""  # nothing to show

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_count": len(self.selected_memories),
            "knowledge_count": len(self.selected_knowledge),
            "skills_count": len(self.selected_skills),
            "state_count": len(self.selected_state),
        }
