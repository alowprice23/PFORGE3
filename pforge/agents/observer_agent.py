from __future__ import annotations
import orjson

from .base_agent import BaseAgent
from pforge.validation.test_runner import PytestRunner
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
        self.test_runner = PytestRunner(project_root=self.source_root)

    async def on_tick(self):
        """
        On each tick, run the test suite. If it fails, publish a
        TESTS_FAILED event.
        """
        import xml.etree.ElementTree as ET

        self.logger.info("Running test suite...")

        test_result = self.test_runner.run()

        if not test_result.junit_xml_path:
            self.logger.error("Test runner failed to produce a JUnit XML report.")
            return

        # Parse the JUnit XML report
        try:
            tree = ET.parse(test_result.junit_xml_path)
            root = tree.getroot()
            testsuite = root.find('testsuite')

            num_failures = int(testsuite.attrib.get('failures', 0))
            num_tests = int(testsuite.attrib.get('tests', 0))
            num_passed = num_tests - num_failures

            # Calculate metrics
            entropy = calculate_entropy(num_failures, num_passed)
            current_state = PuzzleState(
                gaps=num_failures,
                total_tests=num_tests,
                passing_tests=num_passed,
            )
            efficiency = compute_intelligent_efficiency(current_state, {})

            metrics_message = Message(
                type=MsgType.METRICS_UPDATED,
                payload={"entropy": entropy, "efficiency": efficiency}
            )
            await self.publish(MsgType.METRICS_UPDATED.value, metrics_message)
            self.logger.info(f"Published METRICS_UPDATED event with entropy={entropy:.4f} and efficiency={efficiency:.4f}")

            if num_failures > 0:
                self.logger.info(f"Test suite failed with {num_failures} failures.")
                failed_tests = []
                for testcase in testsuite.iter('testcase'):
                    failure = testcase.find('failure')
                    if failure is not None:
                        classname = testcase.attrib.get('classname', '')
                        test_name = testcase.attrib.get('name', '')

                        # Convert classname (e.g., tests.test_buggy_module) to a path
                        test_file_path = classname.replace('.', '/') + ".py"

                        nodeid = f"{test_file_path}::{test_name}"
                        failed_tests.append({
                            "nodeid": nodeid,
                            "traceback": failure.text
                        })

                if failed_tests:
                    message = Message(
                        type=MsgType.TESTS_FAILED,
                        payload={"failed_tests": failed_tests}
                    )
                    await self.publish(MsgType.TESTS_FAILED.value, message)
                    self.logger.info(f"Published TESTS_FAILED event with {len(failed_tests)} failures.")
            else:
                self.logger.info("Test suite passed.")
                message = Message(type=MsgType.TESTS_PASSED, payload={})
                await self.publish(MsgType.TESTS_PASSED.value, message)

        except (ET.ParseError, FileNotFoundError, KeyError) as e:
            self.logger.error(f"Failed to parse JUnit XML report: {e}")
