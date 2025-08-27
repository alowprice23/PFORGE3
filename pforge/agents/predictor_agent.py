from __future__ import annotations
import logging
import os
import orjson
from typing import TYPE_CHECKING, List, Dict

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.gemini_client import GeminiClient
from pforge.llm_clients.budget_meter import BudgetMeter

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus

logger = logging.getLogger(__name__)

class PredictorAgent(BaseAgent):
    """
    Uses an LLM to predict code stubs or changes that could fix a
    reported test failure or specification gap.
    """
    name = "predictor"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus):
        super().__init__(bus)
        self.bus.subscribe(self.name, MsgType.TESTS_FAILED.value)

        # This would be injected in a real system
        budget_meter = BudgetMeter(
            tenant="pforge-dev",
            daily_quota_tokens=1_000_000,
            redis_client=self.bus.redis_client
        )
        self.llm_client = GeminiClient(
            api_key=os.getenv("GEMINI_API_KEY"),
            budget_meter=budget_meter
        )
        self.code_manifest: List[str] = []

    async def on_tick(self):
        """
        Consumes test failures and spec gaps, then asks an LLM for predictions.
        """
        # First, check for a new file manifest to keep our context fresh
        manifest_msg = await self.bus.get(f"{self.name}:manifest", timeout=0.1)
        if manifest_msg and manifest_msg.type == "file_manifest":
             self.code_manifest = manifest_msg.payload.get("files", [])

        # Now, check for a failure to work on
        failure_msg = await self.bus.get(self.name, timeout=0.1)
        if not failure_msg or failure_msg.type != MsgType.TESTS_FAILED:
            return

        logger.info("PredictorAgent consumed TESTS_FAILED event.")
        await self._handle_failure(failure_msg.payload)

    def _build_prompt(self, failed_tests: List[Dict]) -> str:
        """Builds a prompt for the Gemini model."""
        # For now, just use the first failure
        failure = failed_tests[0]
        nodeid = failure.get("nodeid", "Unknown test")
        traceback = failure.get("traceback", "No traceback provided.")

        # A real prompt would be more sophisticated, using file content etc.
        prompt = (
            f"A test has failed: {nodeid}\n\n"
            f"Traceback:\n{traceback}\n\n"
            "Based on this failure, please provide a list of suggestions to fix the issue. "
            "Each suggestion should be a JSON object with 'file_path', 'stub' (the code to add/change), "
            "and 'confidence' (0.0-1.0).\n"
            "Respond with only a valid JSON array of these objects."
        )
        return prompt

    async def _handle_failure(self, payload: dict):
        failed_tests = payload.get("failed_tests", [])
        if not failed_tests:
            return

        prompt = self._build_prompt(failed_tests)

        try:
            response_text = await self.llm_client.chat(prompt)
            suggestions = orjson.loads(response_text)
            if not isinstance(suggestions, list):
                logger.error("LLM did not return a list of suggestions.")
                return
        except Exception as e:
            logger.error(f"Failed to get or parse prediction from LLM: {e}")
            return

        prediction_message = Message(
            type="predictions.made", # This will be a new MsgType
            payload={"suggestions": suggestions}
        )
        await self.publish("predictions.made", prediction_message)
        logger.info(f"Published predictions with {len(suggestions)} suggestions.")
