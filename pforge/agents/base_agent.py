from __future__ import annotations
import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid

from pforge.messaging.amp import AMPMessage
from pforge.messaging.redis_stream import get_redis_client, stream_add

if TYPE_CHECKING:
    from pforge.orchestrator.state_bus import StateBus
    from pforge.orchestrator.efficiency_engine import EfficiencyEngine

class BaseAgent:
    """
    The abstract base class for all pForge agents.

    It provides a common lifecycle FSM, hooks for subclasses to implement,
    and high-level helpers for interacting with the AMP message bus.
    """
    # --- Class attributes to be overridden by subclasses ---
    name: str = "base_agent"
    default_enabled: bool = True
    spawn_weight: float = 1.0

    def __init__(self, state_bus: StateBus, efficiency_engine: EfficiencyEngine):
        self.state_bus = state_bus
        self.efficiency_engine = efficiency_engine
        self.redis_client = get_redis_client()
        self.logger = logging.getLogger(f"pforge.agent.{self.name}")
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def on_startup(self):
        """Called once when the agent is first started."""
        self.logger.info("Agent starting up.")

    async def on_tick(self):
        """The main logic loop for the agent, called periodically."""
        raise NotImplementedError("Subclasses must implement the on_tick method.")

    async def on_shutdown(self):
        """Called once when the agent is shutting down."""
        self.logger.info("Agent shutting down.")

    async def _run_loop(self, tick_interval: float):
        """The internal run loop that manages the agent's lifecycle."""
        self._running = True
        await self.on_startup()

        while self._running:
            try:
                await self.on_tick()
            except Exception as e:
                self.logger.exception(f"An error occurred in the on_tick method: {e}")
            await asyncio.sleep(tick_interval)

        await self.on_shutdown()

    def start(self, tick_interval: float = 5.0):
        """Starts the agent's main processing loop in a background task."""
        if not self._running:
            self._task = asyncio.create_task(self._run_loop(tick_interval))
            self.logger.info(f"Agent '{self.name}' has been started.")

    async def stop(self):
        """Stops the agent's processing loop gracefully."""
        if self._running and self._task:
            self._running = False
            # Allow the current tick to finish, then cancel
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                self.logger.warning("Agent did not shut down gracefully, task was cancelled.")
            self.logger.info(f"Agent '{self.name}' has been stopped.")

    async def send_amp_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        snap_sha: str,
        proof: Optional[Any] = None
    ):
        """Helper to construct and send a standard AMP event."""
        message = AMPMessage(
            type=event_type,
            actor=self.name,
            snap_sha=snap_sha,
            payload=payload,
            proof=proof,
            op_id=str(uuid.uuid4())
        )
        # In a full system, we'd sign the message here.
        # message = sign_amp(message)

        # Publish to the global event stream
        await stream_add(self.redis_client, "pforge:amp:global:events", message)
        self.logger.debug(f"Sent AMP event of type '{event_type}'.")
