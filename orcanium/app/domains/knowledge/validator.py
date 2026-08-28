"""Knowledge Validator — 4 deterministic gates.

No LLM. No embeddings. Pure rule engine.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from orcanium.app.core.db import SessionLocal
from orcanium.app.core.db import KnowledgeEntry

logger = logging.getLogger(__name__)

# Gate 1 — valid categories
VALID_CATEGORIES = {"FACT", "RULE", "REFERENCE", "CONCEPT"}
INVALID_CATEGORIES = {"USER", "MEMORY", "STATE", "SKILL", "TEMPORARY", "WORKFLOW"}

# Gate 2 — temporal/volatile keywords (lowercase)
_TEMPORAL_KEYWORDS = [
    "current price", "current weather", "today's", "this week",
    "as of now", "current time", "current date", "stock price",
    "temperature in", "forecast", "traffic", "news about",
]

# Gate 2 — stable/acceptable keywords
_STABLE_KEYWORDS = [
    "documentation", "reference", "guide", "tutorial", "definition",
    "concept", "principle", "standard", "protocol", "algorithm",
    "framework", "library", "function", "method", "pattern",
    "architecture", "historical", "discovered", "invented",
    "programming", "scientific", "mathematical", "physical law",
]


def validate(content: str, category: str, evidence_count: int = 1,
             existing_entries: Optional[List[str]] = None) -> Dict:
    """Run all 4 validation gates on a knowledge candidate.

    Returns:
        {"status": "approved"|"rejected", "score": 0.0-1.0, "reason": str}
    """
    # Gate 1: Category
    cat_ok, cat_reason, cat_score = _gate_category(category)
    if not cat_ok:
        return {"status": "rejected", "score": 0.0, "reason": cat_reason}

    # Gate 2: Stability
    stab_ok, stab_reason, stab_score = _gate_stability(content)
    if not stab_ok:
        return {"status": "rejected", "score": 0.0, "reason": stab_reason}

    # Gate 3: Evidence
    ev_ok, ev_reason, ev_score = _gate_evidence(evidence_count, content)
    if not ev_ok:
        return {"status": "rejected", "score": 0.0, "reason": ev_reason}

    # Gate 4: Novelty
    nov_ok, nov_reason, nov_score = _gate_novelty(content, existing_entries)

    # Composite score
    final_score = (cat_score * 0.25 + stab_score * 0.30 +
                   ev_score * 0.25 + nov_score * 0.20)

    if nov_ok and final_score >= 0.5:
        return {"status": "approved", "score": round(final_score, 4), "reason": "All gates passed"}
    elif not nov_ok:
        return {"status": "rejected", "score": round(final_score, 4),
                "reason": f"Novelty check failed: {nov_reason}"}
    else:
        return {"status": "rejected", "score": round(final_score, 4),
                "reason": f"Score {final_score:.2f} below threshold 0.5"}


def _gate_category(category: str) -> Tuple[bool, str, float]:
    """Gate 1: Category check."""
    if category in VALID_CATEGORIES:
        return True, "", 1.0
    if category in INVALID_CATEGORIES:
        return False, f"Invalid category: {category}", 0.0
    return False, f"Unknown category: {category}", 0.0


def _gate_stability(content: str) -> Tuple[bool, str, float]:
    """Gate 2: Stability check — reject temporal content."""
    lower = content.lower()
    for kw in _TEMPORAL_KEYWORDS:
        if kw in lower:
            return False, f"Temporal content detected: '{kw}'", 0.0
    stable_hits = sum(1 for kw in _STABLE_KEYWORDS if kw in lower)
    score = min(1.0, 0.5 + stable_hits * 0.1)
    return True, "", score


def _gate_evidence(evidence_count: int, content: str) -> Tuple[bool, str, float]:
    """Gate 3: Evidence check."""
    if evidence_count >= 2:
        return True, "", min(1.0, 0.5 + evidence_count * 0.15)
    # Single observation — check if it looks confident
    uncertainty_markers = ["maybe", "perhaps", "might", "could be", "i think", "possibly", "unclear"]
    lower = content.lower()
    uncertainty = sum(1 for m in uncertainty_markers if m in lower)
    if uncertainty > 0:
        return False, "Single uncertain statement", 0.0
    return True, "", 0.4


def _gate_novelty(content: str,
                  existing_entries: Optional[List[str]] = None) -> Tuple[bool, str, float]:
    """Gate 4: Novelty check — lightweight dedup."""
    if not existing_entries:
        return True, "", 1.0

    normalized = _normalize(content)
    for existing in existing_entries:
        existing_norm = _normalize(existing)
        if normalized == existing_norm:
            return False, "Duplicate content (exact match after normalization)", 0.0
        if len(normalized) > 20 and normalized in existing_norm:
            return False, "Duplicate content (substring match)", 0.2
        if len(existing_norm) > 20 and existing_norm in normalized:
            return False, "Duplicate content (existing is substring)", 0.2

    return True, "", 1.0


def _normalize(text: str) -> str:
    """Normalize text for dedup comparison."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_existing_contents(agent_name: str) -> List[str]:
    """Fetch existing KnowledgeEntry contents for an agent (for novelty gate)."""
    db = SessionLocal()
    try:
        entries = db.query(KnowledgeEntry.content).filter(
            KnowledgeEntry.agent_name == agent_name
        ).all()
        return [e[0] for e in entries]
    finally:
        db.close()
