from orcanium.runtime.agent_factory import create_agent


class FakeAgent:
    def __init__(self, **options):
        self.options = options


def test_agent_factory_forwards_resolved_runtime_options():
    agent = create_agent(
        agent_class=FakeAgent,
        agent_name="coding",
        model="model-a",
        platform="tui",
    )

    assert agent.options == {
        "agent_name": "coding",
        "model": "model-a",
        "platform": "tui",
    }
