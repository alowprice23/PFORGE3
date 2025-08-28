from __future__ import annotations
import logging

from pforge.orchestrator.state_bus import PuzzleState
from pforge.orchestrator.signals import Message, MsgType
from pforge.validation.test_runner import run_tests
from .base_agent import BaseAgent

logger = logging.getLogger("agent.observer")

class ObserverAgent(BaseAgent):
    name = "observer"
    tick_interval = 5.0  # Run tests every 5 seconds

    async def on_startup(self) -> None:
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)

    async def on_tick(self, state: PuzzleState) -> None:
        # Also listen for messages that a patch has been applied
        messages = await self.read_amp()
        if messages:
            # If we got any message, it means a patch was applied, so we should run tests.
            logger.info("ObserverAgent detected a patch, running tests.")
            await self._run_and_report_tests()
            return

        # If no patches, only run tests periodically to avoid spamming
        if state.tick % 3 == 0:
            logger.info("ObserverAgent running periodic tests.")
            await self._run_and_report_tests()

    async def _run_and_report_tests(self) -> None:
        """Runs the test suite and publishes the result."""
        try:
            result = run_tests(test_nodes=[], source_root=self.project.root)
            if result is None:
                logger.error("Test runner returned None.")
                return

            if result.failed > 0 or result.exit_code != 0:
                logger.warning("Tests failed! Publishing TESTS_FAILED.")
                message = Message(
                    type=MsgType.TESTS_FAILED,
                    payload={
                        "report_content": result.report_content,
                        "exit_code": result.exit_code,
                    }
                )
                await self.bus.publish(MsgType.TESTS_FAILED.value, message)
            else:
                logger.info("Tests passed! Publishing QED_EMITTED.")
                message = Message(type=MsgType.QED_EMITTED, payload={})
                await self.bus.publish(MsgType.QED_EMITTED.value, message)
        except Exception as e:
            logger.exception("ObserverAgent failed to run tests: %s", e)
