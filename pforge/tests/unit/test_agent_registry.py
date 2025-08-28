import unittest
from unittest.mock import MagicMock

from pforge.orchestrator.agent_registry import AgentRegistry
from pforge.agents.base_agent import BaseAgent
from pforge.messaging.in_memory_bus import InMemoryBus


# Define dummy agents for testing purposes
class DummyAgent1(BaseAgent):
    name = "dummy_agent_1"
    async def on_tick(self):
        pass

class DummyAgent2(BaseAgent):
    name = "dummy_agent_2"
    async def on_tick(self):
        pass

class AnotherDummyAgent1(BaseAgent):
    name = "dummy_agent_1" # Same name as DummyAgent1
    async def on_tick(self):
        pass

class TestAgentRegistry(unittest.TestCase):

    def setUp(self):
        # Mock config that the registry will use to find agent metadata
        self.mock_cfg = MagicMock()
        # Simulate the structure the AgentRegistry expects: cfg.agents.get(agent_name)
        self.mock_cfg.agents.get.return_value = {
            "spawn_weight": 1.0,
            "some_other_config": "value"
        }
        self.mock_state_bus = MagicMock()
        self.mock_eff_engine = MagicMock()
        self.mock_bus = MagicMock(spec=InMemoryBus)
        self.mock_project = MagicMock()

    def test_agent_discovery_with_injection(self):
        """
        Tests that the AgentRegistry can register agents passed directly to it.
        """
        agents_to_register = [DummyAgent1, DummyAgent2]
        registry = AgentRegistry(
            cfg=self.mock_cfg,
            state_bus=self.mock_state_bus,
            eff_engine=self.mock_eff_engine,
            bus=self.mock_bus,
            project=self.mock_project,
            agents=agents_to_register
        )

        # Check that the injected agents are discovered
        self.assertIn("dummy_agent_1", registry.agent_cls)
        self.assertIs(registry.agent_cls["dummy_agent_1"], DummyAgent1)
        self.assertIn("dummy_agent_2", registry.agent_cls)
        self.assertIs(registry.agent_cls["dummy_agent_2"], DummyAgent2)

    def test_duplicate_agent_name_raises_error(self):
        """
        Tests that the registry raises a ValueError if two agents share the same name.
        """
        agents_with_duplicate = [DummyAgent1, AnotherDummyAgent1]

        with self.assertRaises(ValueError) as cm:
            AgentRegistry(
                cfg=self.mock_cfg,
                state_bus=self.mock_state_bus,
                eff_engine=self.mock_eff_engine,
                bus=self.mock_bus,
                project=self.mock_project,
                agents=agents_with_duplicate
            )

        self.assertIn("Duplicate agent name 'dummy_agent_1'", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
