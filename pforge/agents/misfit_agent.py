from __future__ import annotations
import logging
import os
from typing import TYPE_CHECKING, Dict

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project

logger = logging.getLogger(__name__)

class MisfitAgent(BaseAgent):
    """
    Analyzes a patch that failed tests to determine the likely cause of the
    failure, providing a more intelligent analysis than just a raw traceback.
    """
    name = "misfit"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, patch_manager=None):
        super().__init__(bus, config, project, patch_manager)
        # We listen for rejected patches to analyze them.
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_REJECTED.value)

        budget_meter = BudgetMeter(
            tenant="pforge-dev",
            daily_quota_tokens=1_000_000,
            redis_client=self.bus.redis_client
        )
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=budget_meter
        )

    async def on_tick(self):
        message = await self.bus.get(self.name)
        if not message:
            return

        if message.type == MsgType.FIX_PATCH_REJECTED:
            logger.info("MisfitAgent received a FixPatchRejected command.")
            await self._analyze_failure(message.payload)

    def _build_analysis_prompt(self, patch: str, traceback: str) -> str:
        """Builds the prompt for the LLM to analyze the failure."""
        return (
            "You are a senior software engineer performing a code review. "
            "A junior developer submitted a patch to fix a bug, but the patch caused the tests to fail.\n\n"
            "Here is the patch that was submitted:\n"
            "```diff\n"
            f"{patch}\n"
            "```\n\n"
            "Here is the traceback from the test failure:\n"
            "```\n"
            f"{traceback}\n"
            "```\n\n"
            "Please provide a concise, one-sentence explanation of the likely root cause of the error. "
            "Focus on the logical mistake in the patch. Do not suggest a fix."
        )

    async def _analyze_failure(self, payload: Dict):
        """
        Uses an LLM to analyze a failed patch and publishes the finding.
        """
        patch = payload.get("patch")
        traceback = payload.get("traceback")

        if not patch or not traceback:
            logger.warning("MisfitAgent received a rejected patch message with missing patch or traceback.")
            return

        prompt = self._build_analysis_prompt(patch, traceback)

        try:
            logger.info("MisfitAgent calling LLM for failure analysis...")
            explanation = await self.llm_client.chat([{"role": "user", "content": prompt}])
            logger.info(f"MisfitAgent received analysis: {explanation}")

            # Forward the original payload and add the new analysis.
            misfit_payload = payload.copy()
            misfit_payload["misfit_analysis"] = explanation

            misfit_message = Message(
                type=MsgType.MISFIT_DETECTED,
                payload=misfit_payload,
            )
            await self.publish(MsgType.MISFIT_DETECTED.value, misfit_message)
            logger.info("MisfitAgent published a MisfitDetected message.")

        except Exception as e:
            logger.error(f"MisfitAgent failed during LLM call or processing: {e}")
            # If analysis fails, we do nothing. The PlannerAgent's original
            # retry logic will proceed without the extra analysis.
