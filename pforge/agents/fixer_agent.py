from __future__ import annotations
import logging
import os
import re
import hashlib
from typing import TYPE_CHECKING

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
from pforge.tools.imports import rewrite_imports
import libcst as cst


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
        self.bus.subscribe(self.name, MsgType.REFACTOR_TASK.value)

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
        elif message.type == MsgType.REFACTOR_TASK:
            logger.info("FixerAgent received a RefactorTask command.")
            await self._handle_refactor_task(message.payload)

    async def _handle_refactor_task(self, payload: dict):
        """Handles a refactoring task to move a symbol and update imports."""
        original_path = payload.get('file_path')
        symbol = payload.get('symbol')
        new_path = payload.get('suggestion')
        op_id = payload.get('op_id')
        token = payload.get('capability_token')

        if not all([original_path, symbol, new_path, op_id, token]):
            logger.error(f"Invalid REFACTOR_TASK message received: {payload}")
            return

        self.receive_token(token, op_id)
        logger.info(f"Attempting to refactor '{symbol}' from '{original_path}' to '{new_path}'")

        try:
            # 1. Read the original file and find the symbol's code
            original_content = self.project.read_file(original_path)
            tree = cst.parse_module(original_content)

            symbol_node = None
            for node in tree.body:
                if isinstance(node, (cst.FunctionDef, cst.ClassDef)) and node.name.value == symbol:
                    symbol_node = node
                    break

            if not symbol_node:
                logger.error(f"Could not find symbol '{symbol}' in '{original_path}'")
                return

            symbol_code = cst.Module([symbol_node]).code

            # 2. Remove the symbol from the original file
            class SymbolRemover(cst.CSTTransformer):
                def __init__(self, symbol_name):
                    self.symbol_name = symbol_name

                def leave_FunctionDef(self, original_node, updated_node):
                    if original_node.name.value == self.symbol_name:
                        return cst.RemoveFromParent()
                    return updated_node

                def leave_ClassDef(self, original_node, updated_node):
                    if original_node.name.value == self.symbol_name:
                        return cst.RemoveFromParent()
                    return updated_node

            remover = SymbolRemover(symbol)
            modified_tree = tree.visit(remover)
            self.project.write_file(original_path, modified_tree.code)

            # 3. Add the symbol to the new file
            try:
                new_content = self.project.read_file(new_path)
            except FileNotFoundError:
                new_content = "" # Create a new file if it doesn't exist

            new_tree = cst.parse_module(new_content)
            new_body = list(new_tree.body) + [symbol_node]
            final_tree = new_tree.with_changes(body=new_body)
            self.project.write_file(new_path, final_tree.code)

            # 4. Rewrite all imports
            logger.info(f"Rewriting imports for {symbol} moved from {original_path} to {new_path}")
            rewrite_imports(self.project, symbol, original_path, new_path)

            logger.info(f"Successfully refactored '{symbol}' to '{new_path}'")
            # TODO: Publish a success message?

        except Exception as e:
            logger.error(f"Refactoring failed for symbol '{symbol}': {e}", exc_info=True)
            # TODO: Implement rollback logic

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
        llm_response = ""
        try:
            llm_response = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}])
        except Exception as e:
            logger.error(f"[FixerLog] LLM call failed: {e}")
            # Publish a rejection so the orchestrator can retry if needed
            result_msg_type = MsgType.FIX_PATCH_REJECTED
            result_payload = {
                "file_path": file_path,
                "description": description,
                "failed_test_nodeid": failed_test_nodeid,
                "traceback": f"LLM call failed: {e}",
            }
            fix_is_ok = False
            content_sha_after = content_sha_before
            verification_result = None
        else:
            logger.info("[FixerLog] LLM call complete.")

            match = re.search(r"```python\n(.*?)\n```", llm_response, re.DOTALL)
            if match:
                corrected_content = match.group(1).strip()
            else:
                logger.warning("[FixerLog] Could not find a python markdown block in the LLM response. Using raw response.")
                corrected_content = llm_response

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
                # We can't verify, so we can't proceed. Revert the change.
                self.project.write_file(file_path, original_content)
                return

            # Run the full validation suite: targeted tests and delta type check.
            logger.info(f"[FixerLog] Verifying fix for {file_path} with new validation tools...")
            changed_files = [self.project.root / file_path]

            # 1. Select and run tests
            selected_tests = self.test_selector.select_tests(changed_files)
            if selected_tests is None:
                logger.info("[FixerLog] Running full test suite.")
                test_result = self.test_runner.run()
            else:
                logger.info(f"[FixerLog] Selected {len(selected_tests)} tests to run.")
                test_result = self.test_runner.run(targets=selected_tests)

            # 2. Run delta type check
            logger.info("[FixerLog] Running delta type check...")
            type_check_result = run_delta_type_check(changed_files, self.dep_graph)

            # 3. Determine if the fix is OK
            if not type_check_result.passed:
                logger.warning(f"[FixerLog] MyPy check failed. stdout:\n{type_check_result.stdout}\nstderr:\n{type_check_result.stderr}")

            fix_is_ok = test_result.passed and type_check_result.passed
            verification_result = test_result # For proof bundle

            if fix_is_ok:
                logger.info(f"[FixerLog] Fix successful for {file_path}")
                result_msg_type = MsgType.FIX_PATCH_APPLIED
                result_payload = {
                    "file_path": file_path,
                    "op_id": op_id,
                    "content": corrected_content,
                    "original_content": original_content,
                }

                # Publish a delta signal indicating one gap has been closed.
                delta_message = Message(
                    type=MsgType.GAP_DELTA,
                    payload={"agent_name": self.name, "value": -1}
                )
                await self.publish(MsgType.GAP_DELTA.value, delta_message)
                logger.info("[FixerLog] Published GapDelta signal.")
            else:
                logger.warning(f"[FixerLog] Fix failed for {file_path}")
                # Combine test and type check results for a comprehensive traceback.
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
                    "content": corrected_content, # Add the failed patch content
                }
                self.last_applied_patch = None
                # Revert the failed patch
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
