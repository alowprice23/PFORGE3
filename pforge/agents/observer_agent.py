from __future__ import annotations
import orjson
import subprocess

from .base_agent import BaseAgent
from pforge.validation.test_runner import PytestRunner
from pforge.orchestrator.signals import MsgType, Message
from pforge.orchestrator.state_bus import PuzzleState
from pforge.math_models.entropy import calculate_entropy
from pforge.math_models.efficiency import compute_intelligent_efficiency
from pforge.validation.dep_graph import DependencyGraph
from pforge.validation.coverage_index import CoverageIndex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

class ObserverAgent(BaseAgent):
    """
    The primary sensor of the pForge system. It runs the test suite and
    reports failures to the message bus to kick off the repair cycle.
    """
    name: str = "observer"
    tick_interval: float = 5.0  # Run tests every 5 seconds

    def __init__(
        self,
        bus: InMemoryBus,
        config: Config,
        project: Project,
        test_runner: PytestRunner,
        dep_graph: DependencyGraph,
        coverage_index: CoverageIndex,
    ):
        super().__init__(bus, config, project)
        self.test_runner = test_runner
        self.dep_graph = dep_graph
        self.coverage_index = coverage_index
        self.tick_counter = 0

    async def on_tick(self):
        """
        On each tick, run the test suite. If it fails, publish a
        TESTS_FAILED event.
        """
        import xml.etree.ElementTree as ET
        import uuid
        from pforge.proof.capabilities import issue_token

        op_id = f"observer_tick_{uuid.uuid4()}"
        # Grant the token for this tick's operations
        token = issue_token(self.name, ["exec:test", "exec:lint", "fs:read"], op_id)
        self.receive_token(token, op_id)


        self.tick_counter += 1

        # Rebuild dependency graph every 10 ticks
        if self.tick_counter % 10 == 0:
            if await self.has_capability("fs:read", op_id):
                self.logger.info("Rebuilding dependency graph...")
                self.dep_graph.build_graph()
            else:
                self.logger.warning("ObserverAgent lacks 'fs:read' capability, skipping dependency graph rebuild.")


        # Generate new coverage report if it's stale
        if self.coverage_index.is_stale():
            if await self.has_capability("exec:test", op_id):
                self.coverage_index.generate()
                self.coverage_index.load()
            else:
                self.logger.warning("ObserverAgent lacks 'exec:test' capability, skipping coverage generation.")


        if not await self.has_capability("exec:test", op_id):
            self.logger.error(f"ObserverAgent lacks 'exec:test' capability. Cannot run test suite.")
            return

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

            # Run linter and add to gaps
            linter_gaps = await self._run_linter(op_id)
            total_gaps = num_failures + linter_gaps

            # Calculate metrics
            entropy = calculate_entropy(num_failures, num_passed)
            current_state = PuzzleState(
                gaps=total_gaps,
                total_tests=num_tests,
                passing_tests=num_passed,
            )
            efficiency = compute_intelligent_efficiency(current_state, {})

            metrics_message = Message(
                type=MsgType.METRICS_UPDATED,
                payload={"entropy": entropy, "efficiency": efficiency, "gaps": total_gaps}
            )
            await self.publish(MsgType.METRICS_UPDATED.value, metrics_message)
            self.logger.info(f"Published METRICS_UPDATED event with entropy={entropy:.4f}, efficiency={efficiency:.4f}, gaps={total_gaps}")

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

    async def _run_linter(self, op_id: str) -> int:
        """Runs a linter and returns the number of issues."""
        if not await self.has_capability("exec:lint", op_id):
            self.logger.warning("ObserverAgent lacks 'exec:lint' capability. Skipping linter check.")
            return 0

        self.logger.info("Running linter...")
        try:
            result = subprocess.run(["flake8", "."], capture_output=True, text=True, cwd=self.project.root)
            if result.stdout:
                num_issues = len(result.stdout.strip().split('\n'))
                self.logger.info(f"Linter found {num_issues} issues.")
                return num_issues
            return 0
        except FileNotFoundError:
            self.logger.warning("flake8 not found, skipping linter check.")
            return 0
