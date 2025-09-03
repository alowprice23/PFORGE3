from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.tools.formatters import run_ruff

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class FormatterAgent(BaseAgent):
    """
    An agent that formats code files using a tool like ruff or black.
    """
    name = "formatter"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.FORMAT_FILE.value)

    async def on_tick(self):
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.FORMAT_FILE:
            return

        file_path_str = message.payload.get("file_path")
        if not file_path_str:
            return

        await self._format_file(file_path_str)

    async def _format_file(self, file_path_str: str):
        logger.info(f"FormatterAgent formatting file: {file_path_str}")
        full_path = self.project.root / file_path_str
        if not full_path.exists():
            logger.warning(f"FormatterAgent could not find file to format: {full_path}")
            # Optionally, publish a failure message
            return

        output, exit_code = run_ruff(full_path, fix=True)

        if exit_code == 0:
            logger.info(f"Successfully formatted {file_path_str}")
            formatted_message = Message(
                type=MsgType.FILE_FORMATTED,
                payload={"file_path": file_path_str, "output": output}
            )
            await self.publish(MsgType.FILE_FORMATTED.value, formatted_message)
        else:
            logger.error(f"Failed to format {file_path_str}: {output}")
            formatting_failed_message = Message(
                type=MsgType.FORMATTING_FAILED,
                payload={"file_path": file_path_str, "error": output}
            )
            await self.publish(MsgType.FORMATTING_FAILED.value, formatting_failed_message)
