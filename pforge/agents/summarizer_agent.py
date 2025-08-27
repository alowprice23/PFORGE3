from __future__ import annotations
import logging

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType
from pforge.messaging.redis_stream import stream_read_group, stream_ack
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

logger = logging.getLogger(__name__)

class SummarizerAgent(BaseAgent):
    name = "summarizer_agent"
    group_name = "summarizer_group"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # In a real system, the budget meter would be shared.
        db_path = "pforge/var/budget.db"
        budget_meter = BudgetMeter(db_path=db_path)
        self.llm_client = OpenAIClient(budget_meter=budget_meter)

    async def on_tick(self):
        """
        Listens for FIX.PATCH_APPLIED events and generates a summary.
        """
        messages = await stream_read_group(
            self.redis_client,
            self.group_name,
            self.name,
            {"pforge:amp:global:events": ">"}
        )

        for stream, msg_id, amp_message in messages:
            if amp_message.type == MsgType.FIX_PATCH_APPLIED.value:
                logger.info("SummarizerAgent received a FIX.PATCH_APPLIED event.")

                file_path = amp_message.payload.get('file_path', 'N/A')
                patch = amp_message.payload.get('patch', 'N/A')

                prompt = (
                    f"Please provide a one-sentence summary of the following patch "
                    f"that was applied to the file '{file_path}':\n\n{patch}"
                )

                response = await self.llm_client.generate(prompt)
                summary = response["choices"][0]["message"]["content"]

                logger.info(f"Summary: {summary}")

            await stream_ack(self.redis_client, stream, self.group_name, msg_id)
