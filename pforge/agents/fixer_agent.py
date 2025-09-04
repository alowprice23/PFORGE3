from __future__ import annotations
import logging
import os
import re
import hashlib
from typing import TYPE_CHECKING, Optional
from pydantic import BaseModel, Field, ValidationError

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter
from pforge.proof.bundle import ProofBundle, ProofObligation
from pforge.validation.dep_graph import DependencyGraph
from pforge.validation.coverage_index import CoverageIndex
from pforge.validation.test_runner import PytestRunner
from pforge.validation.selection import TestSelector
from pforge.validation.types import run_delta_type_check


if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project

logger = logging.getLogger(__name__)

class FixerVerdict(BaseModel):
    corrected_code: str = Field(..., description="The complete, corrected content of the file.")


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

        # Initialize the validation tools
        logger.info("Initializing validation tools for FixerAgent...")
        self.dep_graph = DependencyGraph(project_root=self.project.root)
        self.coverage_index = CoverageIndex(project_root=self.project.root)
        # It's important to load the coverage index. If it doesn't exist,
        # the selector will just fall back to guard tests.
        self.coverage_index.load()

        self.test_selector = TestSelector(self.dep_graph, self.coverage_index)
        self.test_runner = PytestRunner(project_root=self.project.root)

    async def on_tick(self):
        message = await self.bus.get(self.name)
        if not message:
            return

        if message.type == MsgType.FIX_TASK:
            logger.info("FixerAgent received a FixTask command.")
            await self._handle_fix_task(message.payload)

    def _build_prompt(self, file_path: str, description: str, original_content: str, failed_fix_info: dict | None = None) -> str:
        schema = FixerVerdict.schema_json(indent=2)
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
            "Respond with a single JSON object that conforms to the following JSON Schema:\n"
            f"```json\n{schema}\n```\n"
            "Do not add any commentary or markdown formatting around the JSON."
        )
        return prompt

    async def _handle_fix_task(self, payload: dict):
        file_path = payload.get('file_path')
        description = payload.get('description')
        failed_test_nodeid = payload.get('failed_test_nodeid')
        op_id = payload.get('op_id')
        token = payload.get('capability_token')
        failed_fix_info = payload.get('failed_fix_info') # Get info about prior failed fixes

        if not all([file_path, description, op_id, token]):
            logger.error(f"Invalid FIX_TASK message received: {payload}")
            return

        self.receive_token(token, op_id)

        logger.info(f"[FixerLog] Attempting to fix file: {file_path} with op_id {op_id}")

        try:
            original_content = self.project.read_file(file_path)
            content_sha_before = hashlib.sha256(original_content.encode()).hexdigest()
        except FileNotFoundError:
            logger.error(f"[FixerLog] File not found: {file_path}. Cannot apply fix.")
            return

        prompt = self._build_prompt(file_path, description, original_content, failed_fix_info)

        logger.info("[FixerLog] Calling LLM...")
        try:
            llm_response = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}])
            verdict = FixerVerdict.parse_raw(llm_response)
            corrected_content = verdict.corrected_code
        except (ValidationError, Exception) as e:
            logger.error(f"[FixerLog] LLM call or validation failed: {e}")
            result_msg_type = MsgType.FIX_PATCH_REJECTED
            result_payload = {
                "file_path": file_path,
                "description": description,
                "failed_test_nodeid": failed_test_nodeid,
                "op_id": op_id,
                "traceback": f"LLM call or validation failed: {e}",
                "content": llm_response if 'llm_response' in locals() else "",
            }
            # Since the fix failed before verification, we create a minimal proof
            proof = ProofBundle(
                tree_sha="dummy_sha",
                venv_lock_sha="dummy_venv_lock_sha",
                constraints=[ProofObligation(id="phi.sem.llm_fix_verified", ok=False)],
                llm_prompt=prompt,
                llm_response=llm_response if 'llm_response' in locals() else "",
            )
            result_message = Message(type=result_msg_type, payload=result_payload)
            result_message.payload["proof"] = proof.model_dump()
            await self.publish(result_msg_type.value, result_message)
            return

        logger.info("[FixerLog] LLM call complete.")

        if not await self.has_capability("fs:write", op_id):
            logger.error(f"Missing 'fs:write' capability for op_id {op_id}. Aborting fix.")
            return

        try:
            self.project.write_file(file_path, corrected_content)
            content_sha_after = hashlib.sha256(corrected_content.encode()).hexdigest()
        except IOError as e:
            logger.error(f"[FixerLog] Failed to write fix to {file_path}: {e}")
            return

        if not await self.has_capability("exec:test", op_id):
            logger.error(f"Missing 'exec:test' capability for op_id {op_id}. Aborting verification.")
            self.project.write_file(file_path, original_content)
            return

        logger.info(f"[FixerLog] Verifying fix for {file_path} with new validation tools...")
        changed_files = [self.project.root / file_path]
        selected_tests = self.test_selector.select_tests(changed_files)
        test_result = self.test_runner.run(targets=selected_tests) if selected_tests else self.test_runner.run()
        type_check_result = run_delta_type_check(changed_files, self.dep_graph)

        fix_is_ok = test_result.passed and type_check_result.passed
        verification_result = test_result

        if fix_is_ok:
            logger.info(f"[FixerLog] Fix successful for {file_path}")
            result_msg_type = MsgType.FIX_PATCH_APPLIED
            result_payload = {
                "file_path": file_path,
                "op_id": op_id,
                "content": corrected_content,
                "original_content": original_content,
            }
            delta_message = Message(type=MsgType.GAP_DELTA, payload={"agent_name": self.name, "value": -1})
            await self.publish(MsgType.GAP_DELTA.value, delta_message)
            logger.info("[FixerLog] Published GapDelta signal.")
        else:
            logger.warning(f"[FixerLog] Fix failed for {file_path}")
            traceback = ""
            if not test_result.passed:
                traceback += f"--- Test Failures ---\n{test_result.stdout}\n{test_result.stderr}\n\n"
            if not type_check_result.passed:
                traceback += f"--- Type Check Failures ---\n{type_check_result.stdout}\n"
            result_msg_type = MsgType.FIX_PATCH_REJECTED
            result_payload = {
                "file_path": file_path,
                "description": description,
                "failed_test_nodeid": failed_test_nodeid,
                "op_id": op_id,
                "traceback": traceback.strip(),
                "content": corrected_content,
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
