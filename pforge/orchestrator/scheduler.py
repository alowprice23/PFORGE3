from __future__ import annotations
import asyncio
import logging
from typing import Dict

from .state_bus import PuzzleState
from .agent_registry import AgentRegistry

log = logging.getLogger("pforge.scheduler")

class AdaptiveScheduler:
    def __init__(self, registry: AgentRegistry, state_bus, cfg) -> None:
        self.registry = registry
        self.state_bus = state_bus
        self.cfg = cfg
        self.active_tasks: Dict[str, asyncio.Task] = {}

    async def tick(self, state: PuzzleState) -> None:
        decisions = self._compute_decisions(state)
        await self._apply_decisions(decisions)

    def _compute_decisions(self, state: PuzzleState) -> Dict[str, str]:
        """Return mapping agent_name -> action ('spawn'|'retain'|'retire')"""
        decisions: Dict[str, str] = {}
        agent_configs = self.cfg.agents.get("agents", {})

        for name, agent_config in agent_configs.items():
            meta = self.registry.meta.get(name, {})
            spawn_threshold = agent_config.get("spawn_threshold", meta.get("spawn_threshold", 0.0))
            retire_threshold = agent_config.get("retire_threshold", meta.get("retire_threshold", 0.0))

            # This is a placeholder for a real utility calculation.
            utility = state.delta_utility.get(name, 0.0)

            if name not in self.active_tasks and utility >= spawn_threshold:
                decisions[name] = "spawn"
            elif name in self.active_tasks and utility <= retire_threshold:
                decisions[name] = "retire"
            else:
                decisions[name] = "retain"
        return decisions

    async def _apply_decisions(self, decisions: Dict[str, str]) -> None:
        for agent_name, action in decisions.items():
            if action == "spawn":
                if agent_name in self.registry.agent_cls:
                    coro = self.registry.instantiate(agent_name)
                    if coro:
                        task = asyncio.create_task(coro.run_loop(), name=f"agent:{agent_name}")
                        self.active_tasks[agent_name] = task
                        log.info("Spawned agent %s", agent_name)
                else:
                    log.warning("Agent %s not found in registry.", agent_name)
            elif action == "retire":
                task = self.active_tasks.pop(agent_name, None)
                if task:
                    task.cancel()
                    log.info("Retired agent %s", agent_name)
            # retain: do nothing
