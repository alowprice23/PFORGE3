from __future__ import annotations
import logging
import os

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter
from pforge.messaging.in_memory_bus import InMemoryBus

logger = logging.getLogger(__name__)

class SummarizerAgent(BaseAgent):
    name = "summarizer_agent"

    def __init__(self, bus: InMemoryBus, *args, **kwargs):
        super().__init__(bus, *args, **kwargs)
        # In a real system, the budget meter would be shared.
        budget_meter = BudgetMeter(
            tenant=self.config.budget.tenant,
            daily_quota_tokens=self.config.budget.daily_quota_tokens,
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

            prompt = (
                f"Please provide a one-sentence summary of the following patch "
                f"that was applied to the file '{file_path}':\n\n{patch}"
            )

            response = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}])
            summary = response.strip()

            logger.info(f"Summary: {summary}")
