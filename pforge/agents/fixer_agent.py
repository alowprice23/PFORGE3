from __future__ import annotations
import logging
import os
import re
import hashlib
from typing import TYPE_CHECKING
from pathlib import Path

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
from pforge.snapshot import ProjectSnapshot
import libcst as cst


if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project

logger = logging.getLogger(__name__)

class FixerAgent(BaseAgent):
    name = "fixer"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, llm_client: OpenAIClient, dep_graph: DependencyGraph, coverage_index: CoverageIndex, test_selector: TestSelector, test_runner: PytestRunner):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.FIX_TASK.value)
        self.bus.subscribe(self.name, MsgType.REFACTOR_TASK.value)

        # Dependencies are now injected
        self.llm_client = llm_client
        self.dep_graph = dep_graph
        self.coverage_index = coverage_index
        self.test_selector = test_selector
        self.test_runner = test_runner

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

        if (not await self.has_capability("fs:read", op_id, target=original_path) or
            not await self.has_capability("fs:write", op_id, target=original_path) or
            not await self.has_capability("fs:write", op_id, target=new_path)):
            logger.error(f"Missing capabilities for refactor op_id {op_id}. Aborting.")
            return

        original_contents = {}
        modified_files = []
        try:
            # 1. Read the original file and find the symbol's code
            original_content = self.project.read_file(original_path)
            original_contents[original_path] = original_content
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
            modified_files.append(original_path)

            # 3. Add the symbol to the new file
            try:
                new_content = self.project.read_file(new_path)
                original_contents[new_path] = new_content
            except FileNotFoundError:
                new_content = "" # Create a new file if it doesn't exist
                original_contents[new_path] = ""


            new_tree = cst.parse_module(new_content)
            new_body = list(new_tree.body) + [symbol_node]
            final_tree = new_tree.with_changes(body=new_body)
            self.project.write_file(new_path, final_tree.code)
            modified_files.append(new_path)

            # 4. Rewrite all imports
            logger.info(f"Rewriting imports for {symbol} moved from {original_path} to {new_path}")
            rewritten_files = rewrite_imports(self.project, symbol, original_path, new_path)
            for file in rewritten_files:
                original_contents[file] = self.project.read_file(file)
                modified_files.append(file)


            logger.info(f"Successfully refactored '{symbol}' to '{new_path}'")
            # TODO: Publish a success message?

        except Exception as e:
            logger.error(f"Refactoring failed for symbol '{symbol}': {e}", exc_info=True)
            # Rollback all modified files
            for file_path, content in original_contents.items():
                self.project.write_file(file_path, content)
            logger.info("Rolled back changes from failed refactoring.")

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
        failed_fix_info = payload.get('failed_fix_info')

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
        llm_response = ""
        verification_result = None
        fix_is_ok = False
        content_sha_after = content_sha_before
        result_msg_type = MsgType.FIX_PATCH_REJECTED # Default to rejected
        result_payload = {
            "file_path": file_path,
            "description": description,
            "failed_test_nodeid": failed_test_nodeid,
            "op_id": op_id,
        }

        try:
            logger.info("[FixerLog] Calling LLM...")
            llm_response = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}])
            logger.info("[FixerLog] LLM call complete.")

            match = re.search(r"```python\n(.*?)\n```", llm_response, re.DOTALL)
            if match:
                corrected_content = match.group(1).strip()
            else:
                logger.warning("[FixerLog] Could not find a python markdown block in the LLM response. Using raw response.")
                corrected_content = llm_response

            if (not await self.has_capability("fs:write", op_id, target=file_path) or
                not await self.has_capability("exec:test", op_id)):
                logger.error(f"Missing 'fs:write' or 'exec:test' capability for op_id {op_id}. Aborting fix.")
                raise Exception("Missing required capabilities.")

            with ProjectSnapshot(self.project) as snapshot:
                sandbox_project = snapshot.project
                logger.info(f"[FixerLog] Created sandbox at {sandbox_project.root}")
                sandbox_project.write_file(file_path, corrected_content)

                # Re-initialize validation tools to point to the sandbox
                sandbox_runner = PytestRunner(project_root=sandbox_project.root)
                sandbox_dep_graph = DependencyGraph(project_root=sandbox_project.root)
                sandbox_coverage_index = CoverageIndex(project_root=sandbox_project.root)
                sandbox_coverage_index.load()
                sandbox_selector = TestSelector(sandbox_dep_graph, sandbox_coverage_index)

                logger.info(f"[FixerLog] Verifying fix in sandbox for {file_path}...")
                changed_files = [sandbox_project.root / file_path]

                selected_tests = sandbox_selector.select_tests(changed_files)
                if selected_tests is None:
                    logger.info("[FixerLog] Running full test suite in sandbox.")
                    test_result = sandbox_runner.run()
                else:
                    logger.info(f"[FixerLog] Selected {len(selected_tests)} tests to run in sandbox.")
                    test_result = sandbox_runner.run(targets=selected_tests)

                verification_result = test_result

                logger.info("[FixerLog] Running delta type check in sandbox...")
                type_check_result = run_delta_type_check(changed_files, sandbox_dep_graph)

                if not type_check_result.passed:
                    logger.warning(f"[FixerLog] MyPy check failed in sandbox. stdout:\n{type_check_result.stdout}\nstderr:\n{type_check_result.stderr}")

                fix_is_ok = test_result.passed and type_check_result.passed

                if fix_is_ok:
                    logger.info(f"[FixerLog] Fix verified in sandbox. Committing change.")
                    snapshot.commit(Path(file_path))
                    content_sha_after = hashlib.sha256(corrected_content.encode()).hexdigest()

                    result_msg_type = MsgType.FIX_PATCH_APPLIED
                    result_payload.update({
                        "content": corrected_content,
                        "original_content": original_content,
                    })
                    # Publish a delta signal indicating one gap has been closed.
                    delta_message = Message(type=MsgType.GAP_DELTA, payload={"agent_name": self.name, "value": -1})
                    await self.publish(MsgType.GAP_DELTA.value, delta_message)
                    logger.info("[FixerLog] Published GapDelta signal.")
                else:
                    logger.warning(f"[FixerLog] Fix failed verification in sandbox. Rolling back changes.")
                    self.project.write_file(file_path, original_content)
                    traceback = ""
                    if not test_result.passed:
                        traceback += f"--- Test Failures ---\n{test_result.stdout}\n{test_result.stderr}\n\n"
                    if not type_check_result.passed:
                        traceback += f"--- Type Check Failures ---\n{type_check_result.stdout}\n"

                    result_payload.update({
                        "traceback": traceback.strip(),
                        "content": corrected_content,
                    })

        except Exception as e:
            logger.error(f"[FixerLog] An error occurred during fix handling: {e}", exc_info=True)
            self.project.write_file(file_path, original_content)
            result_payload["traceback"] = str(e)
            fix_is_ok = False
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
