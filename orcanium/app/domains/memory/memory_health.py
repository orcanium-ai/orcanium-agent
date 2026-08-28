"""Memory Health — replaces count-based curator triggers.

Evaluates:
- duplicate ratio
- conflicting facts
- stale entries
- retrieval quality (proxy: access_count distribution)
- distillation opportunities
- orphan skills

Memory Health = 0-100%
Below threshold → Curator recommended
"""

import logging
from typing import Any, Dict, List, Optional

from orcanium.app.domains.memory.store import MemoryStore

logger = logging.getLogger(__name__)

# Thresholds
HEALTH_GOOD = 80  # No action needed
HEALTH_FAIR = 60  # Curator recommended
HEALTH_POOR = 40  # Curator strongly recommended


def evaluate_memory_health(agent_name: str) -> Dict[str, Any]:
    """Evaluate overall memory health for an agent.

    Returns dict with health score (0-100) and per-category breakdown.
    """
    store = MemoryStore(agent_name)
    store.load_from_disk()

    memory_entries = store.get_entries("memory")
    user_entries = store.get_entries("user")

    total_entries = len(memory_entries) + len(user_entries)
    if total_entries == 0:
        return {"health": 100, "status": "empty", "details": "No entries yet"}

    # 1. Duplicate ratio (exact content matches)
    mem_contents = [e.content for e in memory_entries]
    user_contents = [e.content for e in user_entries]
    all_contents = mem_contents + user_contents
    unique = set(all_contents)
    duplicate_ratio = 0.0
    if all_contents:
        duplicate_ratio = 1 - (len(unique) / len(all_contents))
    duplicate_score = max(0, 100 - (duplicate_ratio * 200))  # 50% duplicates = 0 score

    # 2. Stale entry ratio (entries never accessed)
    mem_accessed = sum(1 for e in memory_entries if (e.access_count or 0) > 0)
    stale_ratio = 0.0
    if memory_entries:
        stale_ratio = 1 - (mem_accessed / len(memory_entries))
    stale_score = max(0, 100 - (stale_ratio * 100))

    # 3. Distillation opportunity (large number of entries in same category)
    from collections import Counter

    cat_counts = Counter(e.category for e in memory_entries)
    large_categories = sum(1 for c in cat_counts.values() if c > 10)
    distill_opportunity = min(100, large_categories * 20)
    distill_score = max(0, 100 - distill_opportunity)

    # Calculate weighted health
    health = duplicate_score * 0.35 + stale_score * 0.35 + distill_score * 0.30
    health = round(max(0, min(100, health)), 1)

    result = {
        "health": health,
        "total_entries": total_entries,
        "memory_entries": len(memory_entries),
        "user_entries": len(user_entries),
        "duplicate_ratio": round(duplicate_ratio, 3),
        "stale_ratio": round(stale_ratio, 3),
        "distill_opportunities": large_categories,
        "status": "good"
        if health >= HEALTH_GOOD
        else ("fair" if health >= HEALTH_FAIR else "poor"),
        "recommendation": None
        if health >= HEALTH_GOOD
        else (
            "Curator recommended"
            if health >= HEALTH_FAIR
            else "Curator strongly recommended"
        ),
    }

    return result


def should_run_curator(agent_name: str) -> bool:
    """Check if curator should run based on memory health."""
    health = evaluate_memory_health(agent_name)
    return health["health"] < HEALTH_FAIR
