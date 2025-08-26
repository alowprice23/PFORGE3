from __future__ import annotations
import importlib
import inspect
import pkgutil
from typing import Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    # This will be a circular import at runtime, so we use a type guard
    from pforge.agents.base_agent import BaseAgent

class AgentRegistry:
    """
    Discovers, registers, and instantiates all available pForge agents.

    This class scans the `pforge.agents` package for all subclasses of
    `BaseAgent` and makes them available to the orchestrator for dynamic
    spawning and management.
    """

    def __init__(self):
        self.agent_classes: Dict[str, Type[BaseAgent]] = {}
        self.agent_configs: Dict[str, Dict] = {}
        self._discover_agents()

    def _discover_agents(self):
        """
        Dynamically imports all modules in the `pforge.agents` package
        to trigger registration of agent classes.
        """
        # We need to import the base_agent first to avoid circular dependencies
        # during the discovery process.
        from pforge.agents import base_agent

        package = importlib.import_module("pforge.agents")

        for module_info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            module = importlib.import_module(module_info.name)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, base_agent.BaseAgent) and obj is not base_agent.BaseAgent:
                    # The agent's name is a class attribute
                    agent_name = getattr(obj, "name", None)
                    if agent_name:
                        self.register_agent(agent_name, obj)

    def register_agent(self, name: str, agent_class: Type[BaseAgent]):
        """
        Registers a single agent class. Can be used for manual registration
        if dynamic discovery is not desired.
        """
        if name in self.agent_classes:
            # This could happen if two agents have the same name attribute
            raise ValueError(f"Agent with name '{name}' is already registered.")

        self.agent_classes[name] = agent_class
        # We can also pull default config from the agent class itself
        self.agent_configs[name] = {
            "enabled": getattr(agent_class, "default_enabled", True),
            "spawn_weight": getattr(agent_class, "spawn_weight", 1.0),
            # etc.
        }
        print(f"Registered agent: {name}")

    def get_agent_class(self, name: str) -> Type[BaseAgent] | None:
        """
        Retrieves the class for a registered agent.
        """
        return self.agent_classes.get(name)

    def get_all_agent_names(self) -> list[str]:
        """
        Returns a list of all registered agent names.
        """
        return list(self.agent_classes.keys())

    def instantiate_agent(self, name: str, **kwargs) -> BaseAgent:
        """
        Creates an instance of a registered agent.

        Args:
            name (str): The name of the agent to instantiate.
            **kwargs: Arguments to pass to the agent's constructor.

        Returns:
            BaseAgent: An instance of the requested agent.

        Raises:
            ValueError: If the agent is not registered.
        """
        agent_class = self.get_agent_class(name)
        if not agent_class:
            raise ValueError(f"No agent registered with the name '{name}'.")

        return agent_class(**kwargs)
