from __future__ import annotations
import asyncio
import logging
import yaml
from typing import Dict

import redis

from .state_bus import StateBus
from .efficiency_engine import EfficiencyEngine
from .agent_registry import AgentRegistry

# Placeholder for the scheduler
class AdaptiveScheduler:
    def __init__(self, agent_registry, state_bus, config):
        pass

    async def tick(self, state):
        pass

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    The central coordinator of the pForge system.

    The Orchestrator runs a main "tick" loop. In each tick, it:
    1. Gathers the latest system state.
    2. Updates the global efficiency score.
    3. Delegates to the AdaptiveScheduler to manage the agent lifecycle.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.tick_interval = config.get("cadence", 1.0)

        # Initialize core components
        self.redis_client = redis.Redis.from_url(
            self.config.get("redis_url", "redis://localhost:6379/0"),
            decode_responses=True
        )
        self.state_bus = StateBus(self.redis_client)
        self.efficiency_engine = EfficiencyEngine(self.config.get("formula_constants", {}))
        self.agent_registry = AgentRegistry()
        self.scheduler = AdaptiveScheduler(self.agent_registry, self.state_bus, self.config)

        self.running = False

    async def tick(self):
        """Performs a single iteration of the orchestration loop."""
        logger.debug("Orchestrator tick...")

        # 1. Get current state
        current_state = self.state_bus.get_snapshot()
        current_state.tick += 1

        # 2. Update efficiency score
        current_state.efficiency = self.efficiency_engine.compute(current_state)

        # 3. Publish the updated state
        self.state_bus.publish_update(current_state)

        # 4. Let the scheduler manage agents
        await self.scheduler.tick(current_state)

    async def run(self):
        """Starts the main orchestration loop."""
        self.running = True
        logger.info("pForge Orchestrator started.")

        while self.running:
            await self.tick()
            await asyncio.sleep(self.tick_interval)

        logger.info("pForge Orchestrator stopped.")

    def stop(self):
        """Stops the orchestration loop."""
        self.running = False

def load_config(config_path: str = "config/settings.yaml") -> Dict:
    """Loads the main YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found at {config_path}. Using default empty config.")
        return {}

def main():
    """Main entry point for running the orchestrator."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Load configuration
    config = load_config()

    # Create and run the orchestrator
    orchestrator = Orchestrator(config)

    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        orchestrator.stop()
        # Allow time for a graceful shutdown
        # In a real scenario, we'd await the run task after stopping
        print("\nOrchestrator shutting down...")

if __name__ == "__main__":
    main()
