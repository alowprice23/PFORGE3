from pforge.agents.base_agent import BaseAgent


class ConcreteTestAgent(BaseAgent):
    """A concrete agent for testing purposes."""
    name = "test_agent"
    tick_interval: float = 1.0

    async def on_tick(self):
        pass  # No-op for most tests
