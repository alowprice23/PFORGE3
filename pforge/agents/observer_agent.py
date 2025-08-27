from __future__ import annotations
from pathlib import Path
import time
import orjson

from .base_agent import BaseAgent
from pforge.validation.test_runner import run_tests
from pforge.orchestrator.signals import MsgType

class ObserverAgent(BaseAgent):
    """
    The primary sensor of the pForge system.

    The ObserverAgent's main job is to run the test suite and report
    failures to the message bus.
    """
    name: str = "observer"

    def __init__(self, state_bus, efficiency_engine, source_root: Path | str):
        super().__init__(state_bus, efficiency_engine)
        self.source_root = Path(source_root)
        self.last_test_run_time = 0

    async def on_tick(self):
        """
        On each tick, run the test suite. If it fails, publish a
        TESTS_FAILED event.
        """
        # To avoid spamming test runs, only run every 5 seconds
        if time.time() - self.last_test_run_time < 5:
            return

        self.logger.info("Observer tick: running test suite...")
        self.last_test_run_time = time.time()

        # Run all tests in the project
        test_result = run_tests(test_nodes=[], source_root=self.source_root)

        if test_result is None:
            self.logger.error("Test runner failed to produce a result.")
            return

        if test_result.failed > 0:
            self.logger.info(f"Test suite failed with {test_result.failed} failures.")
            report_data = orjson.loads(test_result.report_content)

            failed_tests = []
            test_file_paths = set()

            for test in report_data.get("tests", []):
                if test.get("outcome") == "failed":
                    nodeid = test.get("nodeid")
                    failed_tests.append({
                        "nodeid": nodeid,
                        "traceback": test.get("longrepr", "")
                    })
                    if nodeid:
                        test_file_paths.add(nodeid.split("::")[0])

            payload = {
                "timestamp": time.time(),
                "failed_tests": failed_tests,
                "test_file_paths": list(test_file_paths),
                "full_report": test_result.report_content,
            }

            await self.send_amp_event(
                event_type=MsgType.TESTS_FAILED.value,
                payload=payload,
                snap_sha=test_result.report_hash,
            )
            self.logger.info(f"Published TESTS_FAILED event with {len(failed_tests)} failures.")
        else:
            self.logger.info("Test suite passed.")
            # Optionally, publish a TESTS_PASSED event
            await self.send_amp_event(
                event_type=MsgType.TESTS_PASSED.value,
                payload={"timestamp": time.time()},
                snap_sha=test_result.report_hash,
            )
