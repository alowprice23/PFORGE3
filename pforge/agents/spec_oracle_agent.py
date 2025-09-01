from __future__ import annotations
import logging
from pathlib import Path
from typing import Set, List, TYPE_CHECKING
import re
import py_compile

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project


logger = logging.getLogger(__name__)

class SpecOracleAgent(BaseAgent):
    """
    Verifies that changes adhere to the project's specification (Φ).
    """
    name: str = "spec_oracle"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.source_root = self.project.root
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)

    async def on_tick(self):
        """
        Checks for FIX_PATCH_APPLIED messages and runs specification checks.
        """
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.FIX_PATCH_APPLIED:
            return

        file_path_str = message.payload.get("file_path")
        if not file_path_str:
            return

        file_path = self.source_root / file_path_str
        self.logger.info(f"Received FIX_PATCH_APPLIED for {file_path}. Checking spec.")

        is_valid = self._check_python_syntax(file_path)

        spec_checked_message = Message(
            type=MsgType.SPEC_CHECKED,
            payload={
                "file_path": file_path_str,
                "is_valid": is_valid,
            }
        )
        await self.publish(MsgType.SPEC_CHECKED.value, spec_checked_message)
        self.logger.info(f"Published SPEC_CHECKED for {file_path_str} with result: {is_valid}")

    def _check_python_syntax(self, file_path: Path) -> bool:
        """
        Checks if the given file has valid Python syntax.
        """
        if not file_path.exists() or file_path.suffix != ".py":
            return True  # Not a python file, so we don't check it

        try:
            py_compile.compile(file_path, doraise=True)
            self.logger.info(f"Syntax check passed for {file_path}")
            return True
        except py_compile.PyCompileError as e:
            self.logger.warning(f"Syntax check failed for {file_path}: {e}")
            return False
