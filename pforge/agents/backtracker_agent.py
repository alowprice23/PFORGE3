from __future__ import annotations
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

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

            revert_message = Message(
                type="backtrack.completed", # This should be a new MsgType
                payload={"file_path": file_path_str, "status": "reverted"}
            )
            # This message type is not defined, so we'll just log it for now.
            # await self.publish("backtrack.completed", revert_message)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to revert {file_path_str} with git: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during backtrack: {e}")
