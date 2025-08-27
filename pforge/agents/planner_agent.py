from __future__ import annotations
import logging
import uuid
from pathlib import Path

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType
from pforge.messaging.amp import AMPMessage

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    name = "planner_agent"

    def _calculate_priority(self, event_payload: dict) -> float:
        """
        Calculates the priority of a fix task based on a formula.
        """
        impact = event_payload.get("impact", 8)
        frequency = event_payload.get("frequency", 5)
        effort = event_payload.get("effort", 4)
        risk = event_payload.get("risk", 3)

        if effort * risk == 0:
            return float('inf')

        priority = (impact * frequency) / (effort * risk)
        return priority

    def _infer_source_from_test(self, test_path_str: str) -> str:
        """
        Infers the source file path from a test file path.
        """
        test_path = Path(test_path_str)

        # Remove 'tests/' prefix and 'test_' from filename
        parts = list(test_path.parts)
        if 'tests' in parts:
            parts.remove('tests')

        filename = parts[-1]
        if filename.startswith("test_"):
            parts[-1] = filename.replace("test_", "", 1)

        # Reconstruct path, assuming it's relative to the project root
        # For the E2E test, this will result in 'buggy_module.py'
        if len(parts) == 1:
            return parts[0]

        return str(Path(*parts))

    async def on_tick(self):
        """
        Listens for TESTS_FAILED events and dispatches FixTasks.
        """
        amp_message = await self.state_bus.bus.subscribe("pforge:amp:global:events")

        if amp_message.type == MsgType.TESTS_FAILED.value:
            logger.info("PlannerAgent consumed TESTS_FAILED event.")

            payload = amp_message.payload
            failed_tests = payload.get("failed_tests", [])
            test_file_paths = payload.get("test_file_paths", [])

            if not failed_tests or not test_file_paths:
                return

            first_failure = failed_tests[0]
            first_test_file = test_file_paths[0]

            inferred_source_path = self._infer_source_from_test(first_test_file)

            description = (
                f"Fix the bug in '{inferred_source_path}' so that the test "
                f"'{first_failure['nodeid']}' passes. The test failed with the "
                f"following error:\n\n{first_failure['traceback']}"
            )

            priority = self._calculate_priority(payload)

            fix_task_payload = {
                "file_path": inferred_source_path,
                "description": description,
                "priority": priority,
                "failed_test_nodeid": first_failure['nodeid'],
            }

            await self.send_amp_event(
                event_type=MsgType.FIX_TASK.value,
                payload=fix_task_payload,
                snap_sha=amp_message.snap_sha,
            )
            logger.info(f"PlannerAgent dispatched a FixTask for file: {inferred_source_path}")
