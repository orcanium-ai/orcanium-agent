"""Execution Lane — foreground/background task orchestration.

Architecture:
    User Request
        │
        ▼
    Foreground Lane (always wins)
        │
        ├── ConversationLoop → LLM → Tools → LLM → Response
        │
        └── Response delivered ──► Background Lane (async)
                                    ├── Review Agent
                                    ├── Title Generation
                                    ├── Knowledge Promotion
                                    ├── Memory Distiller
                                    ├── Curator
                                    └── Analytics

Foreground always has priority over background.
"""

from orcanium.app.domains.execution.background_lane import BackgroundLane
from orcanium.app.domains.execution.lane_manager import LaneManager

__all__ = [
    "BackgroundLane",
    "LaneManager",
]
