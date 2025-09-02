from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project
    from pforge.sandbox import PatchManager

logger = logging.getLogger(__name__)

class BacktrackerAgent(BaseAgent):
    """
    An agent responsible for reverting changes when a patch fails verification
    or causes a conflict.
    """
    name = "backtracker"
    tick_interval: float = 0.5  # Check for messages frequently

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, patch_manager: PatchManager):
        super().__init__(bus, config, project, patch_manager)
        self.bus.subscribe(self.name, MsgType.VERIFICATION_FAILED.value)
        self.bus.subscribe(self.name, MsgType.CONFLICT_FOUND.value)

    async def on_tick(self):
        """
        On each tick, the Backtracker checks for messages and handles them.
        """
        message = await self.bus.get(self.name)
        if not message:
            return

        if message.type == MsgType.VERIFICATION_FAILED:
            logger.info("BacktrackerAgent received a VerificationFailed command.")
            await self._handle_verification_failed(message.payload)
        elif message.type == MsgType.CONFLICT_FOUND:
            logger.info("BacktrackerAgent received a ConflictFound command.")
            await self._handle_conflict_found(message.payload)

    async def _handle_conflict_found(self, payload: Dict):
        """
        Handles a merge conflict by reverting the specific file to its HEAD state.
        """
        file_path = payload.get("file_path")
        logger.warning(f"Conflict found in {file_path}. Reverting file to HEAD.")

        if self.patch_manager.revert_file(file_path):
            logger.info(f"Successfully reverted {file_path} to HEAD.")
            # Optionally, we could publish a message indicating the revert.
            # For now, we just log it.
        else:
            logger.error(f"Failed to revert {file_path} after conflict.")

    async def _handle_verification_failed(self, payload: Dict):
        """
        Handles a failed verification by reverting the last patch and
        notifying the system that the patch was rejected.
        """
        file_path = payload.get("file_path")
        logger.warning(f"Verification failed for {file_path}. Reverting patch.")

        if self.patch_manager.revert_last_patch():
            logger.info(f"Successfully reverted patch for {file_path}.")

            # Now, we need to trigger the retry logic by publishing a
            # FIX_PATCH_REJECTED message, which the PlannerAgent listens for.
            rejected_message = Message(
                type=MsgType.FIX_PATCH_REJECTED,
                payload=payload,
            )
            await self.publish(MsgType.FIX_PATCH_REJECTED.value, rejected_message)
            logger.info(f"Published FIX_PATCH_REJECTED for {file_path} to trigger retry.")
        else:
            logger.error(f"Failed to revert patch for {file_path}. The repository may be in a bad state.")
            # In a real system, we might want to signal a fatal error here.
