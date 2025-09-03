from __future__ import annotations
import logging
import subprocess
from typing import TYPE_CHECKING, List

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class BacktrackerAgent(BaseAgent):
    """
    Reverts changes that have been identified as conflicts based on a
    minimal hitting set provided by the ConflictDetectorAgent.
    """
    name = "backtracker"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.source_root = self.project.root
        self.bus.subscribe(self.name, MsgType.CONFLICT_ANALYZED.value)

    async def on_tick(self):
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.CONFLICT_ANALYZED:
            return

        files_to_revert: List[str] = message.payload.get("minimal_hitting_set", [])
        if not files_to_revert:
            return

        logger.warning(f"Backtracker received conflict analysis. Reverting files: {files_to_revert}")

        for file_path in files_to_revert:
            await self._revert_file(file_path)

    async def _revert_file(self, file_path_str: str):
        """Reverts a single file using git checkout."""
        try:
            cmd = ["git", "checkout", "HEAD", "--", file_path_str]
            subprocess.run(cmd, cwd=self.source_root, check=True, capture_output=True, text=True)

            logger.info(f"Successfully reverted {file_path_str}.")

            delta_message = Message(
                type=MsgType.BACKTRACK_DELTA,
                payload={"agent_name": self.name, "value": 1}
            )
            await self.publish(MsgType.BACKTRACK_DELTA.value, delta_message)

            revert_message = Message(
                type=MsgType.BACKTRACK_COMPLETED,
                payload={"file_path": file_path_str, "status": "reverted"}
            )
            await self.publish(MsgType.BACKTRACK_COMPLETED.value, revert_message)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to revert {file_path_str} with git: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during backtrack of {file_path_str}: {e}")
