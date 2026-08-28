"""ConversationLoop — the single runtime execution model for Orcanium.

Replaces L0/L1/L2/L3 with a single path:
    ContextPlanner → ContextBuilder → Attention → ConversationLoop → LLM → Tool → LLM → Response

This is the ONLY execution entry point. No duplicate paths.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from orcanium.app.agent.prompt_builder import PromptBuilder
from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.cognition.attention_engine import AttentionEngine
from orcanium.app.domains.cognition.context_builder import ContextBuilder, ContextBundle
from orcanium.app.domains.cognition.context_planner import ContextPlan, ContextPlanner
from orcanium.app.domains.cognition.intent_classifier import Intent, classify
from orcanium.app.domains.conversation.loop import run_conversation
from orcanium.app.tools.toolsets import get_tool_definitions

logger = logging.getLogger(__name__)


@dataclass
class ConversationResult:
    """Result from a single conversation execution."""

    response: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    execution_time_ms: float = 0.0
    context_count: int = 0
    plan: Optional[ContextPlan] = None


class ConversationLoop:
    """Single execution model for all agent conversations.

    Flow:
        1. Classify intent
        2. Create context plan (deterministic, no LLM)
        3. Build context (retrieve only requested stores)
        4. Attention rank (if multiple items)
        5. Build prompt (conditional sections only)
        6. Run conversation loop (LLM → Tools → LLM)
        7. Return response
    """

    def __init__(self, agent_name: str):
        self._agent_name = agent_name
        self._attention = AttentionEngine()

    def execute(
        self,
        user_message: str,
        agent_runtime: Any,
        session_id: str,
        delta_callback: Optional[Callable[[str], None]] = None,
        tool_callback: Optional[Callable[..., None]] = None,
        thinking_callback: Optional[Callable[[str], None]] = None,
        interim_callback: Optional[Callable[[str], None]] = None,
        clarify_callback: Optional[Callable[[str, list], None]] = None,
    ) -> ConversationResult:
        """Execute a single conversation turn end-to-end.

        Args:
            user_message: The user's message text
            agent_runtime: Agent runtime for DB access and config
            session_id: Session ID for conversation persistence
            delta_callback: Called with each text token from LLM streaming
            tool_callback: Called with (name, action, **kwargs) for tool events
        """
        import time

        start = time.time()

        try:
            # 1. Classify intent
            cls_result = classify(user_message)

            # 2. Create context plan
            plan = ContextPlanner.plan(
                intent=cls_result.intent,
                confidence=cls_result.confidence,
                matched_patterns=cls_result.matched_patterns,
            )

            event_bus.emit_simple(
                "WORKFLOW",
                "execution_started",
                self._agent_name,
                {
                    "intent": cls_result.intent.value,
                    "plan": plan.reasoning,
                    "needs_tools": plan.needs_tools,
                },
            )

            # 3. Build context (conditional retrieval)
            bundle = ContextBuilder.build(
                agent_name=self._agent_name,
                query=user_message,
                plan=plan,
            )

            # 4. Build working memory with attention
            selected_memories = self._attention.rank(
                bundle.memories, top_k=min(5, plan.top_k)
            ) if bundle.memories else []
            selected_knowledge = self._attention.rank(
                bundle.knowledge, top_k=min(3, plan.top_k)
            ) if bundle.knowledge else []
            selected_skills = self._attention.rank(
                bundle.skills, top_k=min(3, plan.top_k)
            ) if bundle.skills else []
            selected_state = bundle.state[:2]  # state is small, keep all

            event_bus.emit_simple(
                "WORKFLOW",
                "working_memory_created",
                self._agent_name,
                {
                    "memories": len(selected_memories),
                    "knowledge": len(selected_knowledge),
                    "skills": len(selected_skills),
                    "state": len(selected_state),
                },
            )

            # 5. Build prompt from selected context + snapshot
            from orcanium.app.domains.memory.snapshot import get_agent_snapshot
            from orcanium.app.domains.cognition.working_memory import WorkingMemory

            wm = WorkingMemory(
                selected_memories=selected_memories,
                selected_knowledge=selected_knowledge,
                selected_skills=selected_skills,
                selected_state=selected_state,
            )

            snapshot = get_agent_snapshot(self._agent_name)

            knowledge_content = None
            if selected_knowledge:
                knowledge_content = "\n\n".join(
                    f"- [{k.category}] {k.content[:300]}"
                    for k in selected_knowledge[:5]
                )
            state_content = None
            if selected_state:
                state_content = selected_state[0].content

            system_prompt = PromptBuilder.build(
                soul_content=snapshot.soul,
                user_content=snapshot.user or "",
                memory_content=snapshot.memory or "",
                working_memory=wm,
                skill_content=snapshot.skills,
                knowledge_content=knowledge_content,
                state_content=state_content,
            )

            # 6. Run conversation loop
            from orcanium.app.core.db import Message

            history_msgs = (
                agent_runtime.db.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.timestamp.asc())
                .all()
            )

            messages_payload = [{"role": "system", "content": system_prompt}]
            for m in history_msgs[:-1]:
                messages_payload.append(
                    {
                        "role": "user" if m.sender == "user" else "assistant",
                        "content": m.content,
                    }
                )
            messages_payload.append({"role": "user", "content": user_message})

            tool_definitions = None
            if plan.needs_tools:
                enabled_toolsets = agent_runtime.config.get("toolsets", ["core"])
                tool_definitions = get_tool_definitions(
                    enabled_toolsets=enabled_toolsets
                )

            provider = agent_runtime.config.get("model_provider", "openai")
            model = agent_runtime.config.get("model_name", "gpt-4-turbo")

            # Compress conversation history if it exceeds threshold
            from orcanium.app.domains.conversation.compress import compress_if_needed

            messages_payload = compress_if_needed(
                messages_payload,
                provider=provider,
                model=model,
                agent_id=self._agent_name,
                session_id=session_id,
            )

            max_iterations = agent_runtime.config.get("max_iterations", 10)
            reasoning_effort = agent_runtime.config.get("reasoning_effort")
            conv_result = run_conversation(
                messages=messages_payload,
                provider=provider,
                model=model,
                config=agent_runtime.config,
                tool_definitions=tool_definitions,
                agent_id=self._agent_name,
                session_id=session_id,
                max_iterations=max_iterations,
                reasoning_effort=reasoning_effort,
                delta_callback=delta_callback,
                tool_callback=tool_callback,
                clarify_callback=clarify_callback,
                fallback_model=agent_runtime.config.get("fallback_model"),
            )

            elapsed = (time.time() - start) * 1000

            event_bus.emit_simple(
                "WORKFLOW",
                "execution_completed",
                self._agent_name,
                {
                    "intent": cls_result.intent.value,
                    "elapsed_ms": round(elapsed, 0),
                    "tools_used": len(conv_result.get("tool_calls", [])),
                },
            )

            return ConversationResult(
                response=conv_result.get("response", ""),
                tool_calls=conv_result.get("tool_calls", []),
                input_tokens=conv_result.get("input_tokens", 0),
                output_tokens=conv_result.get("output_tokens", 0),
                execution_time_ms=round(elapsed, 0),
                context_count=len(bundle),
                plan=plan,
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"ConversationLoop failed: {e}")
            event_bus.emit_simple(
                "WORKFLOW",
                "execution_failed",
                self._agent_name,
                {"error": str(e)},
            )
            return ConversationResult(
                response=f"I encountered an issue: {e}",
                execution_time_ms=round(elapsed, 0),
            )
