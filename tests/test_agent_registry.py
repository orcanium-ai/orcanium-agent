from orcanium.runtime.agent_registry import AgentSelection, AgentSelectionError


def test_agent_selection_contract_is_immutable():
    selection = AgentSelection(name="coding", available=("coding", "research"))
    assert selection.name == "coding"
    assert selection.available == ("coding", "research")


def test_agent_selection_error_is_user_facing_value_error():
    assert issubclass(AgentSelectionError, ValueError)
