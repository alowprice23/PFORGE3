import unittest
from pforge.orchestrator.agent_registry import AgentRegistry
from pforge.agents.base_agent import BaseAgent

# Define dummy agents for testing purposes
class DummyAgent1(BaseAgent):
    name = "dummy_agent_1"
    async def on_tick(self):
        pass

class DummyAgent2(BaseAgent):
    name = "dummy_agent_2"
    async def on_tick(self):
        pass

# An agent without a name should not be registered
class UnnamedAgent(BaseAgent):
    async def on_tick(self):
        pass

class TestAgentRegistry(unittest.TestCase):

    def test_agent_discovery(self):
        """
        Tests that the AgentRegistry can discover all BaseAgent subclasses
        that have a 'name' attribute.
        """
        registry = AgentRegistry()

        # Check that named agents are discovered
        self.assertIn("dummy_agent_1", registry.agents)
        self.assertIs(registry.agents["dummy_agent_1"], DummyAgent1)

        self.assertIn("dummy_agent_2", registry.agents)
        self.assertIs(registry.agents["dummy_agent_2"], DummyAgent2)

        # Check that the base agent itself is not included
        self.assertNotIn("base-agent", registry.agents)

        # Check that an agent without a name attribute is not included
        # We find the class by its name in the module, since it has no 'name' attr
        unnamed_agent_class_name = "UnnamedAgent"
        all_agent_classes = [agent.__name__ for agent in registry.agents.values()]
        self.assertNotIn(unnamed_agent_class_name, all_agent_classes)

    def test_duplicate_agent_name_raises_error(self):
        """
        Tests that the registry raises a ValueError if two agents share the same name.
        """
        class AnotherDummyAgent1(BaseAgent):
            name = "dummy_agent_1" # Same name as DummyAgent1
            async def on_tick(self):
                pass

        with self.assertRaises(ValueError):
            AgentRegistry()

if __name__ == "__main__":
    unittest.main()
