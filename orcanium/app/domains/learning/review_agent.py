"""Review Agent — forked agent with restricted tool access for background review.

The review agent inherits the parent's provider/model but operates in a restricted
tool environment. It can only call memory_manage and skill_manage tools.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set

from orcanium.app.core.trace import trace, trace_id
from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.capability.memory_api import memory_manage
from orcanium.app.domains.capability.skill_api import skill_manage
from orcanium.app.domains.capability.user_api import user_manage
from orcanium.app.domains.learning.isolation import ReviewIsolation
from orcanium.app.domains.learning.prompts import (
    _COMBINED_REVIEW_PROMPT,
    _MEMORY_REVIEW_PROMPT,
    _SKILL_REVIEW_PROMPT,
    _USER_REVIEW_PROMPT,
)
from orcanium.app.model.model_gateway import (
    clear_llm_context,
    model_gateway,
    set_llm_context,
    set_llm_purpose,
)

logger = logging.getLogger(__name__)

_in_flight: Set[str] = set()
_in_flight_lock = threading.Lock()


def spawn_review_agent(
    agent_name: str,
    config: Dict[str, Any],
    chat_transcript: str,
    review_type: str = "memory",
    db_session_factory=None,
    session_id: Optional[str] = None,
) -> None:
    """Spawn a forked review agent in a daemon thread."""
    review_key = f"{agent_name}:{review_type}"
    with _in_flight_lock:
        if review_key in _in_flight:
            logger.info(f"Skipping duplicate review for {agent_name} ({review_type})")
            return
        _in_flight.add(review_key)

    thread = threading.Thread(
        target=_run_review_agent,
        args=(
            agent_name,
            config,
            chat_transcript,
            review_type,
            db_session_factory,
            review_key,
            session_id,
        ),
        daemon=True,
    )
    thread.start()
    logger.info(f"Spawned review agent for {agent_name} ({review_type}) in background thread")


def _run_review_agent(
    agent_name: str,
    config: Dict[str, Any],
    chat_transcript: str,
    review_type: str,
    db_session_factory,
    review_key: str,
    session_id: Optional[str],
) -> None:
    """Execute review agent with isolated tool environment."""
    _tid = trace_id()
    _t0 = time.time()
    trace("ENTER", "_run_review_agent", request_id=_tid, purpose="MEMORY_REVIEW", extra=f"review_type={review_type}")
    set_llm_context(agent_name, session_id)
    set_llm_purpose("MEMORY_REVIEW")
    try:
        with ReviewIsolation():
            # Build prompt with current context
            from orcanium.app.domains.memory.store import MemoryStore

            store = MemoryStore(agent_name)
            store.load_from_disk()

            current_memory = "\n".join(
                f"§ [{e.category}] {e.content}" for e in store.get_entries("memory")
            )
            current_user = "\n".join(
                f"§ [{e.category}] {e.content}" for e in store.get_entries("user")
            )

            if review_type == "memory":
                prompt = _MEMORY_REVIEW_PROMPT.format(
                    current_memory=current_memory or "(Empty)",
                    chat_transcript=chat_transcript,
                )
            elif review_type == "user":
                prompt = _USER_REVIEW_PROMPT.format(
                    current_user=current_user or "(Empty)",
                    chat_transcript=chat_transcript,
                )
            elif review_type == "skills":
                prompt = _SKILL_REVIEW_PROMPT.format(
                    current_skills="(Empty)",
                    chat_transcript=chat_transcript,
                )
            else:
                prompt = _COMBINED_REVIEW_PROMPT.format(
                    current_memory=current_memory or "(Empty)",
                    current_user=current_user or "(Empty)",
                    current_skills="(Empty)",
                    chat_transcript=chat_transcript,
                )

            # Run mini conversation loop with tools
            from orcanium.app.domains.conversation.loop import run_conversation

            messages = [
                {
                    "role": "system",
                    "content": "You are a review agent. Use the available tools to update memory and skills based on the conversation.",
                },
                {"role": "user", "content": prompt},
            ]

            conv_result = run_conversation(
                messages=messages,
                provider=config.get("model_provider", "openai"),
                model=config.get("model_name", "gpt-4-turbo"),
                config=config,
                tool_definitions=None,
                agent_id=agent_name,
                session_id=session_id,
            )

            logger.info(
                f"Review agent for {agent_name}: {conv_result.get('response', '')[:100]}"
            )

            # Reset counters on success
            if db_session_factory:
                from orcanium.app.domains.agent.runtime_state import agent_runtime_state

                db = db_session_factory()
                try:
                    if review_type in ("memory", "both"):
                        agent_runtime_state.reset_memory_counter(agent_name, db)
                    if review_type in ("user", "both"):
                        agent_runtime_state.reset_user_counter(agent_name, db)
                    if review_type in ("skills", "both"):
                        agent_runtime_state.reset_skill_counter(agent_name, db)
                finally:
                    db.close()

            event_bus.emit_simple(
                "MEMORY", "review_completed", agent_name, {"review_type": review_type}
            )

            trace("EXIT", "_run_review_agent", request_id=_tid, purpose="MEMORY_REVIEW", elapsed_ms=(time.time() - _t0) * 1000, extra="(complete)")

    except Exception as e:
        logger.warning(f"Review agent failed for {agent_name}: {e}")
        trace("EXIT", "_run_review_agent", request_id=_tid, purpose="MEMORY_REVIEW", elapsed_ms=(time.time() - _t0) * 1000, extra=f"(failed: {e})")
    finally:
        clear_llm_context()
        with _in_flight_lock:
            _in_flight.discard(review_key)
