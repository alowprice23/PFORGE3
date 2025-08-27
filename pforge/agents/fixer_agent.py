from __future__ import annotations
import logging
import os
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter
from pforge.proof.bundle import ProofBundle, ProofObligation
from pforge.validation.test_runner import run_tests

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project

logger = logging.getLogger(__name__)

class FixerAgent(BaseAgent):
    name = "fixer"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.FIX_TASK.value)

        # In a real system, the client would be injected or created by a factory
        # based on config. For now, we'll instantiate one directly.
        # The budget meter would also be shared.
        budget_meter = BudgetMeter(
            tenant="pforge-dev",
            daily_quota_tokens=1_000_000,
            redis_client=self.bus.redis_client # Assuming bus exposes this
        )
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=budget_meter
        )

    async def on_tick(self):
        message = await self.bus.get(self.name)
        if not message:
            return

        if message.type == MsgType.FIX_TASK:
            logger.info("FixerAgent received a FixTask command.")
            await self._handle_fix_task(message.payload)

    async def _handle_fix_task(self, payload: dict):
        file_path = payload['file_path']
        description = payload['description']
        failed_test_nodeid = payload.get('failed_test_nodeid')

        logger.info(f"[FixerLog] Attempting to fix file: {file_path}")
        try:
            original_content = self.project.read_file(file_path)
        except FileNotFoundError:
            logger.error(f"[FixerLog] File not found: {file_path}. Cannot apply fix.")
            return

        prompt = (
            f"The file '{file_path}' has a bug.\n"
            f"The bug is described as: {description}\n\n"
            f"Here is the original content of the file:\n```\n{original_content}\n```\n\n"
            f"Please provide the complete, corrected content of the file '{file_path}'. "
            "Do not add any explanations or comments, only the raw file content, "
            "enclosed in a single ```python ... ``` block."
        )

        logger.info("[FixerLog] Calling LLM...")
        try:
            corrected_content = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}])
        except Exception as e:
            logger.error(f"[FixerLog] LLM call failed: {e}")
            return
        logger.info("[FixerLog] LLM call complete.")

        if corrected_content.startswith("```python"):
            corrected_content = corrected_content[len("```python"):].strip()
        if corrected_content.endswith("```"):
            corrected_content = corrected_content[:-len("```")].strip()

        logger.info(f"[FixerLog] Applying potential fix to {file_path}")
        try:
            self.project.write_file(file_path, corrected_content)
        except IOError as e:
            logger.error(f"[FixerLog] Failed to write fix to {file_path}: {e}")
            return
        logger.info(f"[FixerLog] Applied potential fix to {file_path}")

        logger.info(f"[FixerLog] Verifying fix by running test: {failed_test_nodeid}")
        verification_result = run_tests(
            test_nodes=[failed_test_nodeid] if failed_test_nodeid else [],
            source_root=self.project.root
        )
        logger.info(f"[FixerLog] Verification complete. Result: {verification_result}")

        fix_is_ok = verification_result is not None and verification_result.failed == 0

        proof = ProofBundle(
            tree_sha="dummy_sha",
            venv_lock_sha="dummy_venv_lock_sha",
            constraints=[ProofObligation(id="phi.sem.llm_fix_verified", ok=fix_is_ok)]
        )

        if fix_is_ok:
            result_msg_type = MsgType.FIX_PATCH_APPLIED
            result_payload = {"file_path": file_path}
        else:
            result_msg_type = MsgType.FIX_PATCH_REJECTED
            # Extract traceback for the planner
            traceback = "No verification result."
            if verification_result and verification_result.report_content:
                # For now, just pass the whole report content.
                # A more sophisticated approach would parse this to find the specific error.
                traceback = verification_result.report_content

            result_payload = {
                "file_path": file_path,
                "description": description,
                "failed_test_nodeid": failed_test_nodeid,
                "traceback": traceback,
            }

        result_message = Message(type=result_msg_type, payload=result_payload)
        result_message.payload["proof"] = proof.dict()

        logger.info(f"[FixerLog] Publishing {result_msg_type.value} for {file_path}")
        await self.publish(result_msg_type.value, result_message)
        logger.info(f"[FixerLog] Published {result_msg_type.value} for {file_path}")
