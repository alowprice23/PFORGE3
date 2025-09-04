from __future__ import annotations
import logging
import os
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter
from pforge.messaging.in_memory_bus import InMemoryBus

logger = logging.getLogger(__name__)

class SummaryVerdict(BaseModel):
    summary: str = Field(..., description="A one-sentence summary of the patch.")

class SummarizerAgent(BaseAgent):
    name = "summarizer_agent"

    def __init__(self, bus: InMemoryBus, *args, **kwargs):
        super().__init__(bus, *args, **kwargs)
        # In a real system, the budget meter would be shared.
        budget_meter = BudgetMeter(
            tenant="pforge-dev",
            daily_quota_tokens=1_000_000,
            redis_client=self.bus.redis_client
        )
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=budget_meter
        )
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)


    async def on_tick(self):
        """
        Listens for FIX.PATCH_APPLIED events and generates a summary.
        """
        amp_message = await self.bus.get(self.name, timeout=1.0)
        if amp_message and amp_message.type == MsgType.FIX_PATCH_APPLIED.value:
            logger.info("SummarizerAgent received a FIX.PATCH_APPLIED event.")

            file_path = amp_message.payload.get('file_path', 'N/A')
            patch = amp_message.payload.get('patch', 'N/A')

            schema = SummaryVerdict.schema_json(indent=2)
            prompt = (
                f"Please provide a one-sentence summary of the following patch "
                f"that was applied to the file '{file_path}':\n\n{patch}\n\n"
                "Respond with a single JSON object that conforms to the following JSON Schema:\n"
                f"```json\n{schema}\n```\n"
                "Do not add any commentary or markdown formatting around the JSON."
            )

            try:
                response_text = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}])
                verdict = SummaryVerdict.parse_raw(response_text)
                summary = verdict.summary
                logger.info(f"Summary: {summary}")
            except ValidationError as e:
                logger.error(f"SummarizerAgent failed to validate Pydantic model: {e}\nResponse: {response_text}")
            except Exception as e:
                logger.error(f"SummarizerAgent LLM call or other processing failed: {e}")
