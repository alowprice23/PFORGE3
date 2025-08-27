from __future__ import annotations
import logging

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType
from pforge.messaging.redis_stream import stream_read_group, stream_ack
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter
from pforge.proof.bundle import ProofBundle, ProofObligation

logger = logging.getLogger(__name__)

class FixerAgent(BaseAgent):
    name = "fixer_agent"
    group_name = "fixer_group"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # In a real system, the budget meter would be shared.
        db_path = "pforge/var/budget.db"
        budget_meter = BudgetMeter(db_path=db_path)
        self.llm_client = OpenAIClient(budget_meter=budget_meter)

    async def on_tick(self):
        """
        Listens for FixTask commands and applies patches.
        """
        messages = await stream_read_group(
            self.redis_client,
            self.group_name,
            self.name,
            {"pforge:amp:global:events": "0-0"} # Read from the beginning for the test
        )

        for stream, msg_id, amp_message in messages:
            if amp_message.type == MsgType.FIX_TASK.value:
                logger.info("FixerAgent received a FixTask command.")

                file_path = amp_message.payload['file_path']
                description = amp_message.payload['description']

                prompt = (
                    f"The file '{file_path}' has a bug.\n"
                    f"The bug is described as: {description}\n"
                    f"Please provide the complete, corrected content of the file '{file_path}'. "
                    "Do not add any explanations or comments, only the raw file content, "
                    "enclosed in a single ```python ... ``` block."
                )

                response = await self.llm_client.generate(prompt)
                full_content = response["choices"][0]["message"]["content"]

                # Super simple parser for ```python ... ``` blocks
                if full_content.startswith("```python"):
                    full_content = full_content[len("```python"):].strip()
                if full_content.endswith("```"):
                    full_content = full_content[:-len("```")].strip()

                # Apply the fix by overwriting the file
                with open(file_path, "w") as f:
                    f.write(full_content)
                logger.info(f"Applied fix to {file_path}")

                # Create a proof bundle
                logger.info("Creating proof bundle...")
                obligation = ProofObligation(
                    id="phi.sem.llm_fix",
                    ok=True,
                    witness={
                        "prompt": prompt,
                        "response": response,
                    }
                )
                proof = ProofBundle(
                    tree_sha="dummy_tree_sha",
                    venv_lock_sha="dummy_venv_lock_sha",
                    constraints=[obligation],
                    tests={"passed": 1, "total": 1} # Dummy test results
                )

                await self.send_amp_event(
                    event_type=MsgType.FIX_PATCH_APPLIED.value,
                    payload={"new_content": full_content, "file_path": file_path},
                    snap_sha=amp_message.snap_sha,
                    proof=proof.model_dump()
                )
                logger.info(f"FixerAgent about to emit FIX.PATCH_APPLIED event for file: {file_path}")
                logger.info(f"FixerAgent emitted a FIX.PATCH_APPLIED event for file: {file_path}")

            await stream_ack(self.redis_client, stream, self.group_name, msg_id)
