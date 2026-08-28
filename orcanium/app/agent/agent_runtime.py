import datetime
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from orcanium.app.agent.agent_manager import AgentManager
from orcanium.app.core.db import AgentState, Message
from orcanium.app.core.db import Session as DbSession
from orcanium.app.core.trace import trace, trace_id
from orcanium.app.domains.agent.health import agent_health
from orcanium.app.domains.execution import LaneManager
from orcanium.app.domains.capability.events import (
    OrcaniumEvent, event_bus, SESSION_CREATED, SESSION_ACTIVE,
)
from orcanium.app.model.model_gateway import (
    clear_llm_context,
    model_gateway,
    set_llm_context,
    set_llm_purpose,
)

logger = logging.getLogger(__name__)

_TITLE_GENERATION_PROMPT = (
    "Generate a concise title (5 words or fewer) for a conversation "
    "that starts with this user message. Respond with ONLY the title, "
    "no punctuation, no quotes, no explanation.\n\nMessage: "
)


class AgentRuntime:
    def __init__(self, agent_name: str, db: Session):
        self.agent_name = agent_name
        self.db = db
        self.config = AgentManager.load_agent_config(agent_name)
        if not self.config:
            raise ValueError(f"Agent {agent_name} configuration not found.")

    def _get_or_create_session(self, session_id: Optional[str]) -> DbSession:
        """Retrieves or creates a session database model."""
        if not session_id:
            session_id = str(uuid.uuid4())

        session = self.db.query(DbSession).filter(DbSession.id == session_id).first()
        if not session:
            session = DbSession(
                id=session_id, agent_name=self.agent_name, title="New Chat Session"
            )
            self.db.add(session)

            # Increment agent active sessions
            agent_state = (
                self.db.query(AgentState)
                .filter(AgentState.name == self.agent_name)
                .first()
            )
            if agent_state:
                agent_state.active_sessions = (agent_state.active_sessions or 0) + 1

            self.db.commit()
            self.db.refresh(session)

            event_bus.emit(OrcaniumEvent(
                category="SESSION", event_type=SESSION_CREATED,
                agent_id=self.agent_name, session_id=session.id,
                payload={"title": session.title},
            ))

        return session

    def _generate_title(self, user_message: str, session_id: str) -> str:
        """Use the agent's model to generate a concise session title."""
        _tid = trace_id()
        _t0 = time.time()
        trace("ENTER", "_generate_title", request_id=_tid, purpose="TITLE_GENERATION")
        set_llm_context(self.agent_name, session_id)
        set_llm_purpose("TITLE_GENERATION")
        provider = self.config.get("model_provider", "openai")
        model = self.config.get("model_name", "gpt-4-turbo")
        try:
            title = model_gateway.generate(
                messages=[
                    {"role": "system", "content": _TITLE_GENERATION_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                provider=provider,
                model=model,
                config={"temperature": 0.3, "max_tokens": 30},
            )
            title = title.strip().strip('"').strip("'")
            if title and len(title) > 2 and len(title) < 80:
                trace("EXIT", "_generate_title", request_id=_tid, purpose="TITLE_GENERATION", elapsed_ms=(time.time() - _t0) * 1000)
                return title
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
        trace("EXIT", "_generate_title", request_id=_tid, purpose="TITLE_GENERATION", elapsed_ms=(time.time() - _t0) * 1000, extra="(fallback)")
        return user_message[:40] + "..."

    def _schedule_title_generation(self, session_id: str, user_message: str) -> None:
        """Generate session title in the background lane."""
        def _worker() -> None:
            from orcanium.app.core.db import SessionLocal

            db = SessionLocal()
            try:
                session = db.query(DbSession).filter(DbSession.id == session_id).first()
                if not session or session.title != "New Chat Session":
                    return
                title = self._generate_title(user_message, session_id)
                session.title = title
                db.commit()
            except Exception as e:
                logger.warning(f"Background title generation failed: {e}")
            finally:
                clear_llm_context()
                db.close()

        LaneManager.get_instance().enqueue(
            task_type="title",
            agent_name=self.agent_name,
            fn=_worker,
        )

    def process_message(
        self,
        user_content: str,
        session_id: Optional[str] = None,
        delta_callback=None,
        tool_callback=None,
        thinking_callback=None,
        interim_callback=None,
        clarify_callback=None,
        user_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Receives user message, runs hybrid retrieval, executes context assembly,
        submits message to model via conversation loop (model→tools→model→...),
        updates SQLite models, triggers reflection, and returns final response dictionary.
        """
        _tid = trace_id()
        _t0 = time.time()
        trace("ENTER", "process_message", request_id=_tid)

        session = self._get_or_create_session(session_id)

        # 1. Store User Message
        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session.id,
            sender="user",
            content=user_content,
            timestamp=datetime.datetime.utcnow(),
        )
        self.db.add(user_msg)
        self.db.commit()

        # Update session timestamp
        session.updated_at = datetime.datetime.utcnow()
        self.db.commit()

        # 2. Execute via ConversationLoop (foreground lane — always wins)
        from orcanium.app.domains.cognition.conversation_loop import ConversationLoop

        lane_mgr = LaneManager.get_instance()
        with lane_mgr.foreground():
            set_llm_context(self.agent_name, session.id)
            set_llm_purpose("PRIMARY_RESPONSE")
            try:
                loop = ConversationLoop(self.agent_name)
                conv_result = loop.execute(
                    user_content,
                    self,
                    session.id,
                    delta_callback=delta_callback,
                    tool_callback=tool_callback,
                )
            finally:
                clear_llm_context()
        agent_reply = conv_result.response
        executed_tool_results = conv_result.tool_calls
        input_tokens = conv_result.input_tokens
        output_tokens = conv_result.output_tokens

            # 7. Save Agent Message
        agent_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session.id,
            sender="agent",
            content=agent_reply,
            timestamp=datetime.datetime.utcnow(),
        )
        self.db.add(agent_msg)
        self.db.commit()

        # Record agent activity for health tracking
        agent_health.record_activity(self.agent_name)

        # 8. Trigger Reflection Loop in Background thread (per-agent, nudge-based)
        reflection_status = "disabled"
        if self.config.get("auto_memory", True):
            from orcanium.app.domains.agent.runtime_state import agent_runtime_state

            # Increment per-agent memory counter
            current_mem_val = agent_runtime_state.increment_memory_counter(
                self.agent_name, self.db
            )
            # Increment per-agent skill counter
            current_skill_val = agent_runtime_state.increment_skill_counter(
                self.agent_name, self.db
            )
            nudge_interval = self.config.get("memory_nudge_interval", 10)

            # Check memory and skill nudges independently
            review_types = []
            if current_mem_val >= nudge_interval:
                review_types.append("memory")
            skill_interval = self.config.get("skill_nudge_interval", 10)
            if current_skill_val >= skill_interval:
                review_types.append("skill")

            if review_types:
                should_review = True
                review_type = "both" if len(review_types) == 2 else review_types[0]

            if should_review:
                # Fetch latest chat logs for reflection
                latest_history = (
                    self.db.query(Message)
                    .filter(Message.session_id == session.id)
                    .order_by(Message.timestamp.asc())
                    .all()
                )
                history_payload = [
                    {"role": m.sender, "content": m.content} for m in latest_history
                ]

                transcript = "\n".join(
                    f"{m['role'].upper()}: {m['content']}"
                    for m in history_payload[-10:]
                )

                reflection_status = "pending"
                from orcanium.app.core.db import SessionLocal
                from orcanium.app.domains.learning.review_agent import (
                    spawn_review_agent,
                )

                lane_mgr.enqueue(
                    task_type="review",
                    agent_name=self.agent_name,
                    fn=lambda: spawn_review_agent(
                        agent_name=self.agent_name,
                        config=self.config,
                        chat_transcript=transcript,
                        review_type=review_type,
                        db_session_factory=SessionLocal,
                        session_id=session.id,
                    ),
                )
            else:
                reflection_status = (
                    f"mem_{nudge_interval - current_mem_val}_"
                    f"skill_{skill_interval - current_skill_val}"
                )

        # Update session title in background. User response must not wait for it.
        if session.title == "New Chat Session" and len(user_content) > 5:
            self._schedule_title_generation(session.id, user_content)

        # Track token usage on the session
        if input_tokens or output_tokens:
            session.total_input_tokens = (
                session.total_input_tokens or 0
            ) + input_tokens
            session.total_output_tokens = (
                session.total_output_tokens or 0
            ) + output_tokens
            self.db.commit()

        trace("EXIT", "process_message", request_id=_tid, elapsed_ms=(time.time() - _t0) * 1000)
        return {
            "session_id": session.id,
            "user_message": user_content,
            "agent_response": agent_reply,
            "tools_executed": executed_tool_results,
            "reflection_status": reflection_status,
        }
