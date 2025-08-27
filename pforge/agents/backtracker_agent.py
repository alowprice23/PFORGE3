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

logger = logging.getLogger(__name__)

class BacktrackerAgent(BaseAgent):
    """
    Reverts changes that have been rejected by the verification process.
    """
    name = "backtracker"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, source_root: str | Path = "."):
        super().__init__(bus)
        self.source_root = Path(source_root)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_REJECTED.value)

    async def on_tick(self):
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.FIX_PATCH_REJECTED:
            return

        file_path_str = message.payload.get("file_path")
        if not file_path_str:
            return

        logger.warning(f"Backtracker received rejection for {file_path_str}. Reverting changes.")

        try:
            # Use git to revert the file to its state at HEAD
            cmd = ["git", "checkout", "HEAD", "--", file_path_str]
            subprocess.run(cmd, cwd=self.source_root, check=True)

            logger.info(f"Successfully reverted {file_path_str}.")

            revert_message = Message(
                type="backtrack.completed", # New MsgType
                payload={"file_path": file_path_str, "status": "reverted"}
            )
            await self.publish("backtrack.completed", revert_message)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to revert {file_path_str} with git: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during backtrack: {e}")
