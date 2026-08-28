from orcanium.runtime.turn import run_agent_turn
from orcanium.runtime.configuration import (
    configured_model,
    resolve_startup_model_and_provider,
)


class FullAgent:
    def run_conversation(
        self,
        message,
        conversation_history=None,
        task_id=None,
        stream_callback=None,
        persist_user_message=None,
    ):
        if stream_callback:
            stream_callback("delta")
        return {
            "final_response": message,
            "history": conversation_history,
            "task_id": task_id,
            "persisted": persist_user_message,
        }


class MinimalAgent:
    def run_conversation(self, message):
        return {"final_response": message}


def test_run_agent_turn_forwards_supported_turn_arguments():
    deltas = []

    result = run_agent_turn(
        FullAgent(),
        "hello",
        conversation_history=[{"role": "user", "content": "hello"}],
        task_id="session-1",
        stream_callback=deltas.append,
        persist_user_message="original",
    )

    assert result["final_response"] == "hello"
    assert result["task_id"] == "session-1"
    assert result["persisted"] == "original"
    assert deltas == ["delta"]


def test_run_agent_turn_works_with_a_minimal_agent():
    assert run_agent_turn(MinimalAgent(), "hello") == {"final_response": "hello"}


def test_runtime_configuration_uses_explicit_model_and_detected_provider():
    config = {"model": {"default": "configured-model", "provider": "configured"}}
    detected = resolve_startup_model_and_provider(
        config,
        model_override="requested-model",
        detect_provider=lambda model, provider: (f"{provider}-provider", model),
    )

    assert configured_model(config) == "configured-model"
    assert detected == ("configured-provider", "requested-model")
