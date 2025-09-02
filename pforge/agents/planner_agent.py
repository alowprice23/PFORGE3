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

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, patch_manager=None):
        super().__init__(bus, config, project, patch_manager)
        self.bus.subscribe(self.name, MsgType.TESTS_FAILED.value)
        self.bus.subscribe(self.name, MsgType.FIX_FAILED.value)

    def _infer_source_from_test(self, test_path_str: str) -> str | None:
        """
        Infers a potential source file path from a test file path.

        e.g., 'tests/integration/test_fixer_agent.py' -> 'pforge/agents/fixer_agent.py'
        This is a heuristic and might not always be correct.
        """
        test_path = Path(test_path_str)

        try:
            # Find the path relative to the 'tests' directory
            relative_path = test_path.relative_to("tests")
        except ValueError:
            # If 'tests' is not in the path, we can't infer the source.
            logger.warning(f"Could not determine source for test path: {test_path_str}")
            return None

        # Remove 'test_' from the filename
        source_filename = relative_path.name.replace("test_", "", 1)

        # Look for a corresponding source file in common source directories
        # (e.g., 'pforge', 'src'). This makes the heuristic more robust.
        potential_source_dirs = ["pforge", "src", "."]

        for source_dir in potential_source_dirs:
            potential_path = self.project.root / source_dir / relative_path.parent / source_filename
            if potential_path.exists():
                logger.info(f"Inferred source path: {potential_path}")
                # Return the path relative to the project root, as a string
                return str(potential_path.relative_to(self.project.root))

        logger.warning(f"Could not find a matching source file for: {test_path_str}")
        return None

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

        if not inferred_source_path:
            logger.error(f"Could not infer source path for test {nodeid}. Cannot create a fix task.")
            return

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
        patch = payload.get("patch")
        misfit_analysis = payload.get("misfit_analysis")

        description = (
            f"A previous attempt to fix the bug in '{file_path}' failed.\n"
            f"The original problem was: {original_description}\n\n"
            f"The failed patch was:\n```diff\n{patch}\n```\n\n"
            f"The patch failed with this error:\n```\n{traceback}\n```\n\n"
        )

        if misfit_analysis:
            description += (
                "An AI assistant has analyzed the failure and provided this root cause analysis:\n"
                f"'{misfit_analysis}'\n\n"
            )

        description += "Please analyze all the information and provide a new, corrected solution."


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
