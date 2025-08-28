from __future__ import annotations
import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Dict, Type

from pforge.agents.base_agent import BaseAgent
from pforge.config.models import Config

class AgentRegistry:
    def __init__(self, cfg: Config, bus, state_bus, eff_engine, project, agents: list[Type[BaseAgent]] | None = None) -> None:
        self.cfg = cfg
        self.bus = bus
        self.state_bus = state_bus
        self.eff_engine = eff_engine
        self.project = project
        self.meta: Dict[str, Dict] = {}
        self.agent_cls: Dict[str, Type[BaseAgent]] = {}
        if agents:
            self._register_agents(agents)
        else:
            self._discover_agents()

    def _register_agents(self, agents: list[Type[BaseAgent]]):
        for agent_cls in agents:
            self._register_from_class(agent_cls)

    def _register_from_class(self, obj: Type[BaseAgent]):
        if issubclass(obj, BaseAgent) and obj is not BaseAgent:
            agent_name = getattr(obj, 'name', None)
            if agent_name:
                if agent_name in self.agent_cls:
                    raise ValueError(f"Duplicate agent name '{agent_name}'")
                self.agent_cls[agent_name] = obj
                # Find the config for this agent
                agent_config = self.cfg.agents.get(agent_name)
                if agent_config:
                    self.meta[agent_name] = {
                        "weight": agent_config.get("weight", 1.0),
                        "spawn_threshold": agent_config.get("spawn_threshold", 0.0),
                        "retire_threshold": agent_config.get("retire_threshold", 0.0),
                        "max_tokens_tick": agent_config.get("max_tokens_tick", 5000),
                    }

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
            self._register_from_class(obj)

    def instantiate(self, name: str) -> BaseAgent | None:
        cls = self.agent_cls.get(name)
        if cls:
            return cls(
                bus=self.bus,
                state_bus=self.state_bus,
                eff_engine=self.eff_engine,
                project=self.project,
            )
        return None
