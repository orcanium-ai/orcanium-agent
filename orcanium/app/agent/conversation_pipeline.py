"""ConversationPipeline — lightweight orchestrator for a single conversation turn.

Owns ONLY conversation lifecycle, stage ordering, cancellation, retry flow,
timeout handling, and event emission. Never contains business logic.
"""

import datetime
import logging
import time
import uuid
from typing import Any, Dict, Optional

from app.agent.pipeline_types import (
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageResult,
)
from orcanium.app.agent.turn_context import TurnContext
from orcanium.app.agent.turn_result import TurnResult

logger = logging.getLogger(__name__)


def _stage(func):
    """Decorator that wraps a pipeline stage with timing + event emission."""
    def wrapper(self, ctx: TurnContext, result: TurnResult) -> None:
        stage = getattr(func, "_stage_name", PipelineStage.INTENT_CLASSIFY)
        t0 = time.time()
        sr = StageResult(stage=stage, status=PipelineStatus.RUNNING)
        try:
            func(self, ctx, result)
            sr.status = PipelineStatus.COMPLETED
        except Exception as e:
            sr.status = PipelineStatus.FAILED
            sr.error = str(e)
            logger.error("Stage %s failed: %s", stage.value, e)
        sr.elapsed_ms = (time.time() - t0) * 1000
        result.timings[stage.value] = sr.elapsed_ms
        result.events.append({
            "event_type": f"{stage.value}_{sr.status.value}",
            "elapsed_ms": sr.elapsed_ms,
            "error": sr.error,
        })
        # Also emit through EventBus so all consumers see it
        try:
            from orcanium.app.domains.capability.events import OrcaniumEvent, event_bus
            event_bus.emit(OrcaniumEvent(
                category="TASK",
                event_type=f"{stage.value}_{sr.status.value}",
                agent_id=ctx.agent_name,
                session_id=ctx.session_id,
                payload={"elapsed_ms": sr.elapsed_ms, "error": sr.error},
            ))
        except Exception:
            pass
        if sr.status == PipelineStatus.FAILED:
            result.error = sr.error
    return wrapper


class ConversationPipeline:
    """Orchestrates a single conversation turn through explicit stages.

    Target size: 200-400 LOC.
    Every stage delegates to its domain.
    The pipeline owns orchestration only.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def execute(self, ctx: TurnContext) -> TurnResult:
        """Run the full conversation pipeline for one turn."""
        result = TurnResult(session_id=ctx.session_id)
        t0 = time.time()

        try:
            self._stage_intent_classify(ctx, result)
            if result.error:
                return result

            self._stage_retrieval(ctx, result)
            if result.error:
                return result

            self._stage_attention(ctx, result)

            self._stage_working_memory(ctx, result)

            self._stage_prompt_assembly(ctx, result)
            if result.error:
                return result

            self._stage_model_generate(ctx, result)
            if result.error:
                return result

            self._stage_tool_execute(ctx, result)

            self._stage_memory_commit(ctx, result)

            result.status = PipelineStatus.COMPLETED

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            logger.exception("Pipeline failed for agent '%s'", self.agent_name)

        result.total_elapsed_ms = (time.time() - t0) * 1000
        return result

    # ── Stage implementations ────────────────────────────────────

    def _stage_intent_classify(self, ctx: TurnContext, result: TurnResult) -> None:
        """Classify user intent from the incoming message."""
        try:
            from orcanium.app.domains.cognition.intent_classifier import classify_intent
            ctx.intent = classify_intent(ctx.user_content, ctx.agent_name)
        except Exception:
            ctx.intent = "general"

    def _stage_retrieval(self, ctx: TurnContext, result: TurnResult) -> None:
        """Run retrieval planner + knowledge/memory retrieval."""
        try:
            from orcanium.app.domains.cognition.retrieval import retrieve_all
            retrieved = retrieve_all(ctx.agent_name, ctx.user_content)
            ctx.working_memory = {
                "memories": retrieved.get("memories", []),
                "knowledge": retrieved.get("knowledge", []),
                "skills": retrieved.get("skills", []),
                "state": retrieved.get("state", []),
            }
        except Exception:
            ctx.working_memory = {}

    def _stage_attention(self, ctx: TurnContext, result: TurnResult) -> None:
        """Apply attention engine to select relevant context."""
        if not ctx.working_memory:
            return
        try:
            from orcanium.app.domains.cognition.attention_engine import AttentionEngine
            engine = AttentionEngine()
            ctx.working_memory = engine.rank(ctx.working_memory, ctx.user_content)
        except Exception:
            pass

    def _stage_working_memory(self, ctx: TurnContext, result: TurnResult) -> None:
        """Build working memory snapshot for the prompt."""
        try:
            from orcanium.app.domains.cognition.working_memory import WorkingMemory
            wm = WorkingMemory(
                selected_memories=ctx.working_memory.get("memories", []) if ctx.working_memory else [],
                selected_knowledge=ctx.working_memory.get("knowledge", []) if ctx.working_memory else [],
            )
            ctx.working_memory["prompt_block"] = wm.to_prompt_block()
        except Exception:
            pass

    def _stage_prompt_assembly(self, ctx: TurnContext, result: TurnResult) -> None:
        """Assemble the full prompt from all context sources."""
        from orcanium.app.agent.prompt_builder import PromptBuilder
        builder = PromptBuilder(self.agent_name)
        ctx.prompt = builder.build(
            user_content=ctx.user_content,
            working_memory=ctx.working_memory,
        )

    def _stage_model_generate(self, ctx: TurnContext, result: TurnResult) -> None:
        """Call the model gateway and stream the response."""
        from orcanium.app.model.model_gateway import model_gateway
        from orcanium.app.agent.agent_manager import AgentManager
        from orcanium.app.domains.provider.errors import normalize_error

        config = AgentManager.load_agent_config(self.agent_name)
        provider = config.get("model_provider", "openai")
        model = config.get("model_name", "gpt-4-turbo")
        ctx.provider = provider
        ctx.model = model

        try:
            conv_result = model_gateway.generate(
                messages=[{"role": "user", "content": ctx.prompt}],
                provider=provider,
                model=model,
                config={"temperature": config.get("temperature", 0.7)},
                delta_callback=ctx.delta_callback,
            )
        except Exception as e:
            err = normalize_error(e, provider, model)
            result.error = f"[{err.type.value}] {err.message}"
            result.provider_info = {"provider": provider, "model": model, "error": err.type.value}
            if err.retryable:
                result.error += " (retryable)"
            return

        result.assistant_message = conv_result.get("response", "")
        result.input_tokens = conv_result.get("input_tokens", 0)
        result.output_tokens = conv_result.get("output_tokens", 0)
        result.provider_info = {"provider": provider, "model": model}

    def _stage_tool_execute(self, ctx: TurnContext, result: TurnResult) -> None:
        """Execute tool calls with explicit lifecycle: File Safety → Execution → Redaction."""
        from orcanium.app.domains.capability.file_safety import validate_path, get_read_block_error
        from orcanium.app.domains.capability.redaction import sanitize_tool_output
        from orcanium.app.domains.tool.handlers import handle_tool_calls, parse_tool_calls

        tool_calls = parse_tool_calls(result.assistant_message)
        results = []

        for tc in tool_calls:
            result.events.append({"event_type": "tool_started", "tool": tc.get("name", "?")})

            # 1. File Safety — validate paths before execution
            args = tc.get("arguments", {})
            for path_field in ("path", "file", "source", "destination"):
                if path_field in args:
                    safe, reason = validate_path(str(args[path_field]))
                    if not safe:
                        results.append({"tool": tc.get("name"), "error": f"File safety: {reason}", "status": "rejected"})
                        result.events.append({"event_type": "tool_rejected", "tool": tc.get("name"), "reason": reason})
                        continue

            # 2. Execute
            try:
                from orcanium.app.domains.tool.handlers import execute_single_tool
                output = execute_single_tool(tc, self.agent_name)
            except Exception as e:
                results.append({"tool": tc.get("name"), "error": str(e), "status": "failed"})
                result.events.append({"event_type": "tool_failed", "tool": tc.get("name"), "error": str(e)})
                continue

            # 3. Redaction — sanitize output before returning
            if isinstance(output, str):
                output = sanitize_tool_output(output)
            elif isinstance(output, dict):
                for k, v in output.items():
                    if isinstance(v, str):
                        output[k] = sanitize_tool_output(v)

            results.append({"tool": tc.get("name"), "output": output, "status": "completed"})
            result.events.append({"event_type": "tool_completed", "tool": tc.get("name")})

        result.tool_results = results

    def _stage_memory_commit(self, ctx: TurnContext, result: TurnResult) -> None:
        """Commit the conversation turn to memory."""
        try:
            from orcanium.app.domains.memory.store import MemoryStore
            store = MemoryStore(self.agent_name)
            store.load_from_disk()
            store.add(target="memory", content=f"{ctx.user_content}\n→ {result.assistant_message[:500]}", category="CONTEXT")
        except Exception:
            pass
