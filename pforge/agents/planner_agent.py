from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.math_models.priority import compute_task_priority

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project


logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    name = "planner"
    tick_interval: float = 1.0  # Check for messages every second

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.TESTS_FAILED.value)
        self.bus.subscribe(self.name, MsgType.FIX_FAILED.value)

    def _infer_source_from_test(self, test_path_str: str) -> str:
        """
        Infers the source file path from a test file path.
        e.g., 'pforge/tests/integration/test_fixer_agent.py' -> 'pforge/agents/fixer_agent.py'
        """
        test_path = Path(test_path_str)

        # Remove 'tests/' prefix and 'test_' from filename
        parts = list(test_path.parts)

        # Find the 'tests' directory and rebuild the path from the part after it
        try:
            tests_index = parts.index("tests")
            # This assumes the structure inside tests mirrors the structure in pforge
            source_parts = parts[tests_index + 1 :]
        except ValueError:
            # If 'tests' is not in the path, assume it's a top-level test
            source_parts = parts

        if not source_parts:
            return ""

        filename = source_parts[-1]
        if filename.startswith("test_"):
            source_parts[-1] = filename.replace("test_", "", 1)

        # Reconstruct path relative to the pforge package root
        return str(Path("pforge") / Path(*source_parts))

    async def on_tick(self):
        """
        Listens for TESTS_FAILED and FIX_FAILED events and dispatches FIX_TASKs.
        """
        message = await self.bus.get(self.name)
        if not message:
            return

        if message.type == MsgType.TESTS_FAILED:
            await self._handle_tests_failed(message.payload)
        elif message.type == MsgType.FIX_FAILED:
            await self._handle_fix_failed(message.payload)

    async def _handle_tests_failed(self, payload: dict):
        logger.info("PlannerAgent consumed TESTS_FAILED event.")

        failed_tests = payload.get("failed_tests", [])
        if not failed_tests:
            return

        # For now, focus on the first failure
        first_failure = failed_tests[0]
        nodeid = first_failure.get("nodeid", "")
        if not nodeid:
            return

        test_file_path = nodeid.split("::")[0]
        inferred_source_path = self._infer_source_from_test(test_file_path)

        description = (
            f"Fix the bug in '{inferred_source_path}' so that the test "
            f"'{nodeid}' passes. The test failed with the "
            f"following error:\n\n{first_failure['traceback']}"
        )

        # Use the new priority calculation
        priority = compute_task_priority(payload)

        fix_task_message = Message(
            type=MsgType.FIX_TASK,
            payload={
                "file_path": inferred_source_path,
                "description": description,
                "priority": priority,
                "failed_test_nodeid": nodeid,
            },
        )

        await self.publish(MsgType.FIX_TASK.value, fix_task_message)
        logger.info(f"Dispatched FIX_TASK for file: {inferred_source_path}")

    async def _handle_fix_failed(self, payload: dict):
        logger.info("PlannerAgent consumed FIX_FAILED event.")

        file_path = payload.get("file_path")
        original_description = payload.get("description")
        traceback = payload.get("traceback")

        description = (
            f"A previous attempt to fix the bug in '{file_path}' failed. "
            f"The original problem was:\n{original_description}\n\n"
            f"The previous fix failed with this error:\n{traceback}\n\n"
            "Please analyze the previous mistake and provide a different solution."
        )

        # For now, we'll reuse the priority from the failed task payload if it exists.
        priority = payload.get("priority", 0.5)

        fix_task_message = Message(
            type=MsgType.FIX_TASK,
            payload={
                "file_path": file_path,
                "description": description,
                "priority": priority,
                "failed_test_nodeid": payload.get("failed_test_nodeid"),
            },
        )

        await self.publish(MsgType.FIX_TASK.value, fix_task_message)
        logger.info(f"Dispatched new FIX_TASK for file: {file_path} (retry)")
