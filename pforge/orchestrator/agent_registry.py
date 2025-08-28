from __future__ import annotations
import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Dict, Type

from pforge.agents.base_agent import BaseAgent

class AgentRegistry:
    def __init__(self, cfg, state_bus, eff_engine) -> None:
        self.cfg = cfg
        self.state_bus = state_bus
        self.eff_engine = eff_engine
        self.meta: Dict[str, Dict] = {}
        self.agent_cls: Dict[str, Type[BaseAgent]] = {}
        self._discover_agents()

    def _discover_agents(self) -> None:
        """Auto-import all modules in agents/ and register classes."""
        try:
            package = importlib.import_module("pforge.agents")
            for mod_info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                module = importlib.import_module(mod_info.name)
                self._register_from_module(module)
        except Exception as e:
            print(f"Could not discover agents: {e}")

    def _register_from_module(self, module: ModuleType) -> None:
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseAgent) and obj is not BaseAgent:
                agent_name = getattr(obj, 'name', None)
                if agent_name:
                    self.agent_cls[agent_name] = obj
                    # Find the config for this agent
                    agent_config = next((item for item in self.cfg.get("agents", []) if item["name"] == agent_name), None)
                    if agent_config:
                        self.meta[agent_name] = {
                            "weight": agent_config.get("spawn_weight", 1.0),
                            "spawn_threshold": agent_config.get("spawn_threshold", 0.0),
                            "retire_threshold": agent_config.get("retire_threshold", 0.0),
                            "max_tokens_tick": agent_config.get("max_tokens_tick", 5000),
                        }

    def instantiate(self, name: str) -> BaseAgent | None:
        cls = self.agent_cls.get(name)
        if cls:
            return cls(self.state_bus, self.eff_engine)
        return None
