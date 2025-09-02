from __future__ import annotations
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message, BacktrackDelta

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class BacktrackerAgent(BaseAgent):
    """
    Reverts changes that have been identified as conflicts.
    """
    name = "backtracker"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.source_root = self.project.root
        self.bus.subscribe(self.name, MsgType.CONFLICT_FOUND.value)

    async def on_tick(self):
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.CONFLICT_FOUND:
            return

        file_path_str = message.payload.get("file_path")
        if not file_path_str:
            return

        logger.warning(f"Backtracker received conflict for {file_path_str}. Reverting changes.")

        try:
            # Use git to revert the file to its state at HEAD
            cmd = ["git", "checkout", "HEAD", "--", file_path_str]
            subprocess.run(cmd, cwd=self.source_root, check=True, capture_output=True, text=True)

            logger.info(f"Successfully reverted {file_path_str}.")

            # Publish a delta signal indicating a backtrack occurred.
            delta_message = Message(
                type=MsgType.BACKTRACK_DELTA,
                payload={"agent_name": self.name, "value": 1}
            )
            await self.publish(MsgType.BACKTRACK_DELTA.value, delta_message)
            logger.info("[BacktrackerLog] Published BacktrackDelta signal.")

            # The original code mentioned publishing a "backtrack.completed" event.
            # This is a good idea for orchestration, so let's define and publish it.
            # I'll need to add BACKTRACK_COMPLETED to the MsgType enum later.
            revert_message = Message(
                type="backtrack.completed",
                payload={"file_path": file_path_str, "status": "reverted"}
            )
            # For now, let's assume the topic is the same as the message type string.
            await self.publish("backtrack.completed", revert_message)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to revert {file_path_str} with git: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during backtrack: {e}")
