from __future__ import annotations
import logging
import os
import orjson
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

class PredictorAgent(BaseAgent):
    """
    Uses an LLM to predict the likelihood that a proposed patch will
    successfully fix a bug without introducing regressions.
    """
    name = "predictor"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, patch_manager=None):
        super().__init__(bus, config, project, patch_manager)
        self.bus.subscribe(self.name, MsgType.PROPOSED_PATCH.value)

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

        if message.type == MsgType.PROPOSED_PATCH:
            logger.info("PredictorAgent received a ProposedPatch command.")
            await self._predict_patch_success(message.payload)

    def _build_prediction_prompt(self, patch: str, description: str) -> str:
        """Builds the prompt for the LLM to predict patch success."""
        return (
            "You are a senior software engineer acting as an expert code reviewer. "
            "Your task is to predict the success of a proposed code patch.\n\n"
            "The original problem description is:\n"
            f"'{description}'\n\n"
            "Here is the patch that was generated to solve the problem:\n"
            "```diff\n"
            f"{patch}\n"
            "```\n\n"
            "Based on your expertise, estimate the confidence that this patch correctly solves the described problem "
            "without introducing any new bugs or regressions. Provide only a single JSON object in the format "
            '{"confidence": <value>}, where <value> is a float between 0.0 (no confidence) and 1.0 (absolute confidence).'
        )

    async def _predict_patch_success(self, payload: Dict):
        """
        Uses an LLM to predict the success of a patch and publishes the prediction.
        """
        patch = payload.get("patch")
        description = payload.get("description")

        if not patch:
            logger.warning("PredictorAgent received a proposed patch message with no patch.")
            # Default to low confidence if there's no patch to analyze
            prediction_confidence = 0.0
        else:
            prompt = self._build_prediction_prompt(patch, description)
            try:
                logger.info("PredictorAgent calling LLM for success prediction...")
                response_text = await self.llm_client.chat([{"role": "user", "content": prompt}])
                verdict = orjson.loads(response_text)
                prediction_confidence = float(verdict.get("confidence", 0.0))
                logger.info(f"PredictorAgent received prediction. Confidence: {prediction_confidence}")

            except (orjson.JSONDecodeError, TypeError, ValueError) as e:
                logger.error(f"PredictorAgent failed to parse LLM response: {e}. Defaulting to low confidence.")
                prediction_confidence = 0.1 # Default to low confidence on parse failure
            except Exception as e:
                logger.error(f"PredictorAgent failed during LLM call: {e}. Defaulting to low confidence.")
                prediction_confidence = 0.1 # Default to low confidence on API failure

        # Forward the original payload and add the new prediction.
        prediction_payload = payload.copy()
        prediction_payload["prediction_confidence"] = prediction_confidence

        prediction_message = Message(
            type=MsgType.PREDICTION_MADE,
            payload=prediction_payload,
        )
        await self.publish(MsgType.PREDICTION_MADE.value, prediction_message)
        logger.info("PredictorAgent published a PredictionMade message.")
