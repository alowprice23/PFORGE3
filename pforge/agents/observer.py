from __future__ import annotations
import logging
import orjson
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.validation.test_runner import run_tests

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project

logger = logging.getLogger(__name__)

class ObserverAgent(BaseAgent):
    name = "observer"
    tick_interval: float = 5.0  # Run tests every 5 seconds

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, patch_manager=None):
        super().__init__(bus, config, project, patch_manager)
        # This agent doesn't need to subscribe to anything, it's a sensor.

    async def on_tick(self):
        """
        On each tick, the Observer runs the test suite to check the
        current state of the project.
        """
        logger.info("[ObserverLog] Running tests...")

        # For now, we run all tests. In the future, this could be more targeted.
        result = run_tests(test_nodes=[], source_root=self.project.root)

        if not result:
            logger.error("[ObserverLog] Test runner failed to produce a result.")
            return

        if result.failed > 0:
            logger.warning(f"[ObserverLog] {result.failed} test(s) failed.")

            report_data = orjson.loads(result.report_content)
            failed_tests_processed = []
            for test in report_data.get("tests", []):
                if test.get("outcome") == "failed":
                    failed_tests_processed.append({
                        "nodeid": test.get("nodeid"),
                        "traceback": test.get("longrepr", "")
                    })

            message = Message(
                type=MsgType.TESTS_FAILED,
                payload={
                    "failed_tests": failed_tests_processed,
                    "failed": result.failed,
                    "passed": result.passed,
                }
            )
            await self.publish(MsgType.TESTS_FAILED.value, message)

        elif result.passed > 0:
            logger.info(f"[ObserverLog] All {result.passed} test(s) passed.")
            message = Message(
                type=MsgType.TESTS_PASSED,
                payload={
                    "passed": result.passed,
                }
            )
            await self.publish(MsgType.TESTS_PASSED.value, message)

        else:
            logger.info("[ObserverLog] No tests were run or found.")
