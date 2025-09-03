from __future__ import annotations
import orjson

from .base_agent import BaseAgent
from pforge.validation.test_runner import run_tests
from pforge.orchestrator.signals import MsgType, Message
from pforge.orchestrator.state_bus import PuzzleState
from pforge.math_models.entropy import calculate_entropy
from pforge.math_models.efficiency import compute_intelligent_efficiency

class ObserverAgent(BaseAgent):
    """
    The primary sensor of the pForge system. It runs the test suite and
    reports failures to the message bus to kick off the repair cycle.
    """
    name: str = "observer"
    tick_interval: float = 5.0  # Run tests every 5 seconds

    def __init__(self, bus, config, project):
        super().__init__(bus, config, project)
        self.source_root = self.project.root

    async def on_tick(self):
        """
        On each tick, run the test suite. If it fails, publish a
        TESTS_FAILED event.
        """
        self.logger.info("Running test suite...")

        test_result = run_tests(test_nodes=[], source_root=self.source_root)

        if test_result is None:
            self.logger.error("Test runner failed to produce a result.")
            return

        # Calculate metrics
        entropy = calculate_entropy(test_result.failed, test_result.passed)
        # Efficiency calculation requires a state object. We create a temporary
        # one here representing the state observed in this tick.
        current_state = PuzzleState(
            gaps=test_result.failed,
            total_tests=test_result.total,
            passing_tests=test_result.passed,
        )
        efficiency = compute_intelligent_efficiency(current_state, {})

        metrics_message = Message(
            type=MsgType.METRICS_UPDATED,
            payload={
                "entropy": entropy,
                "efficiency": efficiency,
            }
        )
        await self.publish(MsgType.METRICS_UPDATED.value, metrics_message)
        self.logger.info(f"Published METRICS_UPDATED event with entropy={entropy:.4f} and efficiency={efficiency:.4f}")

        if test_result.failed > 0:
            self.logger.info(f"Test suite failed with {test_result.failed} failures.")

            try:
                report_data = orjson.loads(test_result.report_content)
            except orjson.JSONDecodeError:
                self.logger.error("Failed to decode test report JSON.")
                return

            failed_tests = []
            for test in report_data.get("tests", []):
                if test.get("outcome") == "failed":
                    failed_tests.append({
                        "nodeid": test.get("nodeid"),
                        "traceback": test.get("longrepr", "")
                    })

            if failed_tests:
                message = Message(
                    type=MsgType.TESTS_FAILED,
                    payload={
                        "failed_tests": failed_tests,
                    }
                )
                await self.publish(MsgType.TESTS_FAILED.value, message)
                self.logger.info(f"Published TESTS_FAILED event with {len(failed_tests)} failures.")
        else:
            self.logger.info("Test suite passed.")
            message = Message(type=MsgType.TESTS_PASSED, payload={})
            await self.publish(MsgType.TESTS_PASSED.value, message)
