from __future__ import annotations
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.orchestrator.state_bus import PuzzleState
    from pforge.project import Project


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the pForge system.

    Defines the basic lifecycle (setup, run, shutdown) and provides
    a common interface for interacting with the message bus.
    """
    # --- Class-level metadata for the scheduler/registry ---
    name: str = "base-agent"
    tick_interval: float = 1.0  # Default seconds between on_tick calls

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        if not bus:
            raise ValueError("A message bus instance is required.")
        self.bus = bus
        self.config = config
        self.project = project
        self.logger = logging.getLogger(f"pforge.agent.{self.name}")
        self._is_running = False

    async def run_loop(self):
        """The main execution loop for the agent, called by the Orchestrator."""
        self._is_running = True
        await self.on_startup()
        self.logger.info("Agent '%s' started.", self.name)

        while self._is_running:
            try:
                # In a full implementation, the agent would get the latest
                # PuzzleState from the StateBus here. For now, on_tick is parameter-less.
                await self.on_tick()
            except asyncio.CancelledError:
                self.logger.info("Agent '%s' was cancelled.", self.name)
                break
            except Exception:
                self.logger.exception("An error occurred in agent '%s' on_tick.", self.name)

            await asyncio.sleep(self.tick_interval)

        await self.on_shutdown()
        self.logger.info("Agent '%s' shut down.", self.name)

    def stop(self):
        """Signals the agent to stop its execution loop."""
        self.logger.info("Stopping agent '%s'...", self.name)
        self._is_running = False

    # --- Hooks for subclasses to implement ---

    async def on_startup(self):
        """Called once when the agent is starting up."""
        pass

    @abstractmethod
    async def on_tick(self):
        """
        The main logic of the agent, called periodically.
        Subclasses must implement this method.
        """
        raise NotImplementedError

    async def on_shutdown(self):
        """Called once when the agent is shutting down."""
        pass

    async def publish(self, topic: str, message: Any):
        """A simple helper to publish a message to a topic on the bus."""
        await self.bus.publish(topic, message)
