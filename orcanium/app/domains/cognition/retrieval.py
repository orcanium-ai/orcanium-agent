"""Keyword Retrieval Engine — lean, deterministic retrieval without embeddings.

No vector database. No reranker. No semantic model.

Retrieval signals:
    - Exact match
    - Phrase match
    - Partial match
    - Tag match

Common interface for: Memory, Skills, Knowledge, State
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.memory.store import MemoryStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieval result with metadata."""

    source: str  # "memory", "user", "skill", "knowledge", "state"
    content: str
    relevance_score: float = 0.0
    matched_terms: List[str] = field(default_factory=list)
    category: str = "OTHER"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "content": self.content[:150],
            "relevance_score": self.relevance_score,
            "matched_terms": self.matched_terms[:5],
            "category": self.category,
        }


@dataclass
class RetrievalBundle:
    """Bundled results from all retrieval sources."""

    memories: List[RetrievalResult] = field(default_factory=list)
    skills: List[RetrievalResult] = field(default_factory=list)
    knowledge: List[RetrievalResult] = field(default_factory=list)
    state: List[RetrievalResult] = field(default_factory=list)

    def all(self) -> List[RetrievalResult]:
        return self.memories + self.skills + self.knowledge + self.state

    def count(self) -> int:
        return (
            len(self.memories)
            + len(self.skills)
            + len(self.knowledge)
            + len(self.state)
        )


# ── Memory Retrieval ──────────────────────────────────────────


def retrieve_memory(
    agent_name: str, query: str, top_k: int = 10
) -> List[RetrievalResult]:
    """Retrieve from MEMORY.md and USER.md using keyword scoring."""
    store = MemoryStore(agent_name)
    store.load_from_disk()
    results: List[RetrievalResult] = []

    query_lower = query.lower()
    query_words = set(query_lower.split())

    for entry in store.get_entries("memory"):
        score = _score_relevance(query_lower, query_words, entry.content.lower())
        if score > 0:
            results.append(
                RetrievalResult(
                    source="memory",
                    content=entry.content,
                    relevance_score=score,
                    category=entry.category,
                    metadata={
                        "importance": entry.importance,
                        "confidence": entry.confidence,
                    },
                )
            )

    for entry in store.get_entries("user"):
        score = _score_relevance(query_lower, query_words, entry.content.lower())
        if score > 0:
            results.append(
                RetrievalResult(
                    source="user",
                    content=entry.content,
                    relevance_score=score,
                    category=entry.category,
                    metadata={
                        "importance": entry.importance,
                        "confidence": entry.confidence,
                    },
                )
            )

    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results[:top_k]


# ── Skill Retrieval ──────────────────────────────────────────


def retrieve_skills(
    agent_name: str, query: str, top_k: int = 10
) -> List[RetrievalResult]:
    """Retrieve from ACTIVE skills using keyword scoring."""
    results: List[RetrievalResult] = []
    query_lower = query.lower()
    query_words = set(query_lower.split())

    try:
        from orcanium.app.domains.capability.skill_api import skill_manage

        skills_result = skill_manage("retrieve", agent_name)
        for skill in skills_result.get("skills", []):
            if skill.get("state") != "ACTIVE":
                continue
            skill_text = f"{skill['title']} {skill['description']}".lower()
            score = _score_relevance(query_lower, query_words, skill_text)
            if score > 0:
                results.append(
                    RetrievalResult(
                        source="skill",
                        content=f"# {skill['title']}\n{skill['description']}",
                        relevance_score=score,
                        category="SKILL_REFERENCE",
                        metadata={
                            "skill_id": skill.get("id"),
                            "use_count": skill.get("use_count", 0),
                        },
                    )
                )
    except Exception as e:
        logger.warning(f"Skill retrieval failed: {e}")

    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results[:top_k]


# ── Knowledge Retrieval ───────────────────────────────────────


def retrieve_knowledge(
    agent_name: str, query: str, top_k: int = 10
) -> List[RetrievalResult]:
    """Retrieve from KnowledgeEngine (RAG) using keyword scoring."""
    results: List[RetrievalResult] = []
    query_lower = query.lower()
    query_words = set(query_lower.split())

    try:
        from orcanium.app.core.db import SessionLocal
        from orcanium.app.domains.knowledge.knowledge_engine import KnowledgeEngine

        db = SessionLocal()
        try:
            chunks = KnowledgeEngine.retrieve(db, query, top_n=top_k)
            for chunk in chunks:
                content = chunk.get("content", "")
                if not content:
                    continue
                score = _score_relevance(query_lower, query_words, content.lower())
                results.append(
                    RetrievalResult(
                        source="knowledge",
                        content=content[:500],
                        relevance_score=score if score > 0 else 0.5,
                        category="KNOWLEDGE",
                        metadata={"doc_name": chunk.get("doc_name", "unknown")},
                    )
                )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Knowledge retrieval failed: {e}")

    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results[:top_k]


# ── State Retrieval ───────────────────────────────────────────


def retrieve_state(
    agent_name: str, query: str, top_k: int = 5
) -> List[RetrievalResult]:
    """Retrieve from current agent state."""
    results: List[RetrievalResult] = []
    query_lower = query.lower()
    query_words = set(query_lower.split())

    try:
        from orcanium.app.domains.state.state_layer import get_state

        state = get_state(agent_name)
        state_text = f"{state.current_goal} {state.current_plan} {' '.join(state.current_tasks)} {' '.join(state.current_blockers)}"
        score = _score_relevance(query_lower, query_words, state_text.lower())
        if score > 0:
            results.append(
                RetrievalResult(
                    source="state",
                    content=f"Goal: {state.current_goal}\nStatus: {state.current_status}\nTasks: {len(state.current_tasks)}\nBlockers: {len(state.current_blockers)}",
                    relevance_score=score + 0.2,  # State relevance boost
                    category="STATE",
                    metadata={"status": state.current_status},
                )
            )
    except Exception as e:
        logger.warning(f"State retrieval failed: {e}")

    return results[:top_k]


# ── Scoring ───────────────────────────────────────────────────


def _score_relevance(query_lower: str, query_words: set, content_lower: str) -> float:
    """Compute relevance score (0.0-1.0) between query and content."""
    if not query_lower or not content_lower:
        return 0.0

    score = 0.0

    # Exact match → high score
    if query_lower == content_lower:
        return 1.0

    # Phrase match → very high score
    if query_lower in content_lower:
        score = 0.85

    # Partial phrase match
    for phrase_len in range(len(query_words), 1, -1):
        import itertools

        for combo in itertools.combinations(query_words, phrase_len):
            phrase = " ".join(combo)
            if phrase in content_lower:
                score = max(score, 0.6 + (phrase_len / len(query_words)) * 0.3)

    # Word overlap
    content_words = set(content_lower.split())
    if query_words and content_words:
        overlap = query_words & content_words
        if overlap:
            overlap_score = len(overlap) / len(query_words)
            score = max(score, min(0.7, overlap_score * 1.2))

    return round(min(1.0, score), 3)
