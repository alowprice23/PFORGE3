from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class ConflictDetectorAgent(BaseAgent):
    """
    Detects conflicts based on the results of specification checks.
    """
    name: str = "conflict_detector"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.SPEC_CHECKED.value)

    async def on_tick(self):
        """
        Checks for SPEC_CHECKED messages and publishes CONFLICT_FOUND if a check failed.
        """
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.SPEC_CHECKED:
            return

        is_valid = message.payload.get("is_valid")
        file_path_str = message.payload.get("file_path")

        if not is_valid:
            logger.warning(f"Conflict detected in {file_path_str} due to failed spec check.")
            conflict_message = Message(
                type=MsgType.CONFLICT_FOUND,
                payload={"file_path": file_path_str}
            )
            await self.publish(MsgType.CONFLICT_FOUND.value, conflict_message)
            logger.info(f"Published CONFLICT_FOUND for {file_path_str}.")
