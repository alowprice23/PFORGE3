from __future__ import annotations
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

from pforge.proof.capabilities import verify_token, InvalidCapabilityError
from pforge.proof.redaction import scrub
from pforge.orchestrator.signals import Message

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
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
        self._capability_tokens: Dict[str, str] = {} # Map op_id to token

    def receive_token(self, token: str, op_id: str):
        """
        Receives and stores a capability token for a future operation.
        The token is indexed by its operation ID.
        Verification is deferred until the capability is checked.
        """
        if not op_id:
            self.logger.warning("Cannot receive a token without an op_id.")
            return
        self.logger.info(f"Received capability token for op_id: {op_id}")
        self._capability_tokens[op_id] = token

    async def has_capability(self, permission: str, op_id: str) -> bool:
        """
        Checks if the agent holds a valid capability token for the given
        permission and operation ID.
        """
        token = self._capability_tokens.get(op_id)
        if not token:
            self.logger.warning(f"No capability token found for op_id: {op_id}")
            return False

        try:
            payload = await verify_token(token, self.bus.redis_client)
            # Ensure the token's actor matches this agent
            if payload.get("actor") != self.name:
                self.logger.error(f"Token actor mismatch: token is for '{payload.get('actor')}', but I am '{self.name}'")
                return False

            # Check if the required permission is in the token's scope
            if permission in payload.get("scope", []):
                self.logger.info(f"Capability '{permission}' for op_id '{op_id}' is valid.")
                return True
            else:
                self.logger.warning(f"Capability '{permission}' not in scope for op_id '{op_id}'.")
                return False
        except InvalidCapabilityError as e:
            self.logger.error(f"Token for op_id '{op_id}' is invalid: {e}")
            # Once a token is invalid, remove it.
            del self._capability_tokens[op_id]
            return False

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

    async def publish(self, topic: str, message: Message):
        """
        A helper to publish a message to a topic on the bus.
        The message payload is automatically scrubbed for sensitive data before publishing.
        """
        # Scrub the payload automatically before publishing
        scrubbed_payload, report = scrub(message.payload)

        if report.total_redactions > 0:
            self.logger.info(f"Redacted {report.total_redactions} item(s) from message to topic '{topic}'. Details: {report.redacted_counts}")

        # Create a new message with the scrubbed payload to ensure immutability
        scrubbed_message = Message(
            type=message.type,
            payload=scrubbed_payload
        )

        await self.bus.publish(topic, scrubbed_message)
