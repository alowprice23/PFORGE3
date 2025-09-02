from __future__ import annotations
import logging
import os
import re
import hashlib
import difflib
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

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, patch_manager=None):
        super().__init__(bus, config, project, patch_manager)
        self.bus.subscribe(self.name, MsgType.FIX_TASK.value)
        self.bus.subscribe(self.name, MsgType.PREDICTION_MADE.value)

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
        elif message.type == MsgType.PREDICTION_MADE:
            logger.info("FixerAgent received a PredictionMade command.")
            await self._handle_prediction_made(message.payload)

    def _build_prompt(self, file_path: str, description: str, original_content: str, failed_fix_info: dict | None = None) -> str:
        prompt = (
            f"The file '{file_path}' has a bug.\n"
            f"The bug is described as: {description}\n\n"
            f"Here is the original content of the file:\n```python\n{original_content}\n```\n\n"
        )

        if failed_fix_info:
            prompt += (
                "A previous attempt to fix this bug failed. Here is the failed patch and the resulting error:\n"
                f"Failed Patch:\n```python\n{failed_fix_info['content']}\n```\n"
                f"Resulting Error:\n```\n{failed_fix_info['traceback']}\n```\n\n"
            )

        prompt += (
            "Please provide the complete, corrected content of the file. "
            "Only change the necessary code and adhere to the existing coding style. "
            "Do not add any new public APIs. "
            "Return only the raw file content, enclosed in a single ```python ... ``` block."
        )
        return prompt

    def _create_patch(self, original_content: str, corrected_content: str, file_path: str) -> str:
        """Creates a patch using difflib."""
        diff = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            corrected_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)

    def _calculate_churn_from_patch(self, patch: str) -> int:
        """Calculates the code churn (added + deleted lines) from a patch."""
        added = sum(1 for line in patch.splitlines() if line.startswith('+') and not line.startswith('++'))
        deleted = sum(1 for line in patch.splitlines() if line.startswith('-') and not line.startswith('--'))
        return added + deleted

    async def _handle_prediction_made(self, payload: dict):
        """
        Handles the logic after a prediction has been made about a patch.
        Applies the patch and runs tests if confidence is high.
        """
        # For now, we'll use a simple confidence threshold. This could come from config.
        confidence_threshold = 0.5
        prediction_confidence = payload.get("prediction_confidence", 0.0)

        file_path = payload["file_path"]
        description = payload["description"]
        failed_test_nodeid = payload["failed_test_nodeid"]
        patch = payload["patch"]
        churn = payload["churn"]
        corrected_content = payload["corrected_content"]
        original_content = payload["original_content"]
        content_sha_before = payload["content_sha_before"]
        prompt = payload["prompt"]
        llm_response = payload["llm_response"]

        if prediction_confidence < confidence_threshold:
            logger.warning(f"Prediction confidence {prediction_confidence} is below threshold {confidence_threshold}. Rejecting patch for {file_path}.")
            result_msg_type = MsgType.FIX_PATCH_REJECTED
            result_payload = {
                "file_path": file_path,
                "description": description,
                "failed_test_nodeid": failed_test_nodeid,
                "traceback": f"Patch rejected due to low prediction confidence: {prediction_confidence}",
                "patch": patch,
                "churn": churn,
            }
            # Since the file was never written, we don't need to revert it.
            # We also don't have a verification result.
            fix_is_ok = False
            content_sha_after = content_sha_before
            verification_result = None

        else:
            logger.info(f"Prediction confidence {prediction_confidence} is high. Applying and verifying patch for {file_path}.")
            try:
                self.project.write_file(file_path, corrected_content)
                content_sha_after = hashlib.sha256(corrected_content.encode()).hexdigest()
            except IOError as e:
                logger.error(f"[FixerLog] Failed to write fix to {file_path}: {e}")
                return

            test_file = failed_test_nodeid.split("::")[0] if failed_test_nodeid else None
            logger.info(f"[FixerLog] Verifying fix by running tests in: {test_file or 'all tests'}")

            verification_result = run_tests(
                test_nodes=[test_file] if test_file else [],
                source_root=self.project.root
            )

            fix_is_ok = verification_result is not None and verification_result.failed == 0

            if fix_is_ok:
                logger.info(f"[FixerLog] Fix successful for {file_path}")
                result_msg_type = MsgType.FIX_PATCH_APPLIED
                result_payload = {
                    "file_path": file_path,
                    "patch": patch,
                    "churn": churn,
                    "description": description,
                    "failed_test_nodeid": failed_test_nodeid,
                }
            else:
                logger.warning(f"[FixerLog] Fix failed for {file_path}")
                traceback = "No verification result."
                if verification_result and verification_result.report_content:
                    traceback = verification_result.report_content

                result_msg_type = MsgType.FIX_PATCH_REJECTED
                result_payload = {
                    "file_path": file_path,
                    "description": description,
                    "failed_test_nodeid": failed_test_nodeid,
                    "traceback": traceback,
                    "patch": patch,
                    "churn": churn,
                }
                self.project.write_file(file_path, original_content)
                content_sha_after = content_sha_before

        proof = ProofBundle(
            tree_sha="dummy_sha",
            venv_lock_sha="dummy_venv_lock_sha",
            constraints=[ProofObligation(id="phi.sem.llm_fix_verified", ok=fix_is_ok)],
            tests=verification_result.to_dict() if verification_result else None,
            file_path=file_path,
            content_sha_before=content_sha_before,
            content_sha_after=content_sha_after,
            llm_prompt=prompt,
            llm_response=llm_response,
        )
        result_message = Message(type=result_msg_type, payload=result_payload)
        result_message.payload["proof"] = proof.model_dump()

        logger.info(f"[FixerLog] Publishing {result_msg_type.value} for {file_path}")
        await self.publish(result_msg_type.value, result_message)


    async def _handle_fix_task(self, payload: dict):
        """
        Handles a FIX_TASK message by generating a patch and publishing it
        for prediction.
        """
        file_path = payload['file_path']
        description = payload['description']
        failed_test_nodeid = payload.get('failed_test_nodeid')

        logger.info(f"[FixerLog] Generating a patch for file: {file_path}")

        try:
            original_content = self.project.read_file(file_path)
            content_sha_before = hashlib.sha256(original_content.encode()).hexdigest()
        except FileNotFoundError:
            logger.error(f"[FixerLog] File not found: {file_path}. Cannot apply fix.")
            return

        prompt = self._build_prompt(file_path, description, original_content)

        logger.info("[FixerLog] Calling LLM...")
        try:
            llm_response = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}])
        except Exception as e:
            logger.error(f"[FixerLog] LLM call failed: {e}")
            # If LLM fails, we can't propose a patch, so we reject immediately.
            rejected_payload = {
                "file_path": file_path,
                "description": description,
                "failed_test_nodeid": failed_test_nodeid,
                "traceback": f"LLM call failed: {e}",
                "patch": "", "churn": 0,
            }
            rejected_message = Message(type=MsgType.FIX_PATCH_REJECTED, payload=rejected_payload)
            await self.publish(MsgType.FIX_PATCH_REJECTED.value, rejected_message)
            return

        logger.info("[FixerLog] LLM call complete.")

        match = re.search(r"```python\n(.*?)\n```", llm_response, re.DOTALL)
        if match:
            corrected_content = match.group(1).strip()
        else:
            logger.warning("[FixerLog] Could not find a python markdown block in the LLM response. Using raw response.")
            corrected_content = llm_response

        patch = self._create_patch(original_content, corrected_content, file_path)
        churn = self._calculate_churn_from_patch(patch)

        # Instead of applying, we publish a proposal for the PredictorAgent.
        proposal_payload = {
            "file_path": file_path,
            "description": description,
            "failed_test_nodeid": failed_test_nodeid,
            "patch": patch,
            "churn": churn,
            "original_content": original_content,
            "corrected_content": corrected_content,
            "content_sha_before": content_sha_before,
            "prompt": prompt,
            "llm_response": llm_response,
        }

        proposal_message = Message(type=MsgType.PROPOSED_PATCH, payload=proposal_payload)
        await self.publish(MsgType.PROPOSED_PATCH.value, proposal_message)
        logger.info(f"Published PROPOSED_PATCH for {file_path}")
