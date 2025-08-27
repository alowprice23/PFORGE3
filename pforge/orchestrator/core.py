from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Type

import yaml

from pforge.agents.base_agent import BaseAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.agent_registry import AgentRegistry
from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.math_models.efficiency import compute_intelligent_efficiency

logger = logging.getLogger("pforge.orchestrator")


class OrchestratorConfig(dict):
    """Typed wrapper around settings.yaml values."""
    @classmethod
    def load(cls, path: str = "config/settings.yaml") -> "OrchestratorConfig":
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            return cls(raw)
        except FileNotFoundError:
            logger.warning("Config file not found at %s. Using default empty config.", path)
            return cls({})


class Orchestrator:
    """
    The central coordinator of the pForge system. It registers agents and
    runs their main loops, facilitating communication via an in-memory bus.
    """

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.bus = InMemoryBus()
        self.state_bus = StateBus(self.bus)
        self.agent_registry = AgentRegistry()
        self.agents: List[BaseAgent] = []

    def setup_agents(self):
        """
        Discovers and instantiates all available agents from the registry.
        """
        for name, agent_class in self.agent_registry.agents.items():
            # In a real system, you might pass agent-specific config here
            agent_instance = agent_class(bus=self.bus)
            self.agents.append(agent_instance)
            logger.info("Instantiated agent: %s", name)

    async def run(self):
        """Starts the agent run loops and the message bus."""
        logger.info("Orchestrator starting...")
        if not self.agents:
            logger.warning("No agents registered. Orchestrator will exit.")
            return

        # Start the message bus
        bus_task = asyncio.create_task(self.bus.start(), name="InMemoryBus")

        # Start all registered agents
        agent_tasks = [asyncio.create_task(agent.run_loop()) for agent in self.agents]

        try:
            await asyncio.gather(bus_task, *agent_tasks)
        except asyncio.CancelledError:
            logger.info("Orchestrator run cancelled.")
        finally:
            logger.info("Orchestrator shutting down.")
            for task in agent_tasks:
                task.cancel()
            bus_task.cancel()
            await asyncio.gather(bus_task, *agent_tasks, return_exceptions=True)
            logger.info("Orchestrator finished.")

    async def single_tick_update(self):
        """
        Performs a single update of the global puzzle state.
        This can be called periodically or triggered by specific events.
        """
        state = self.state_bus.get_snapshot()
        state.tick += 1

        constants = self.config.get("formula_constants", {})
        state.efficiency = compute_intelligent_efficiency(state, constants)

        await self.state_bus.publish_update(state)
        logger.debug("Orchestrator tick %d: Efficiency=%.2f", state.tick, state.efficiency)


def main():
    """Example main entry point for running the orchestrator."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    config = OrchestratorConfig.load()
    orchestrator = Orchestrator(config)
    orchestrator.setup_agents()

    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\nOrchestrator shutting down by user request...")

if __name__ == "__main__":
    # This is for demonstration. In the actual app, the CLI or server would instantiate and run the orchestrator.
    main()
