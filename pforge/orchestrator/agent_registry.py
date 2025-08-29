from __future__ import annotations
import importlib
import inspect
import pkgutil
from typing import Dict, Type

from pforge.agents.base_agent import BaseAgent

class AgentRegistry:
    """
    Discovers all available agent classes within the `pforge.agents` package.
    """

    def __init__(self):
        self.agents: Dict[str, Type[BaseAgent]] = {}
        self._discover_agents()

    def _discover_agents(self):
        """
        Dynamically imports all modules in `pforge.agents` to find subclasses
        of BaseAgent and registers them by their `name` attribute.
        """
        # The `pforge.agents` package should handle its own imports to ensure
        # all agent modules are loaded when the package is imported.
        import pforge.agents

        for subclass in BaseAgent.__subclasses__():
            agent_name = getattr(subclass, 'name', None)
            if agent_name and agent_name != "base-agent":
                if agent_name in self.agents:
                    raise ValueError(f"Duplicate agent name '{agent_name}' found.")
                self.agents[agent_name] = subclass
