from __future__ import annotations
import logging
import time
import time
from pathlib import Path
import importlib

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter
from pforge.proof.bundle import ProofBundle, ProofObligation
from pforge.validation.test_runner import run_tests

logger = logging.getLogger(__name__)

class FixerAgent(BaseAgent):
    name = "fixer_agent"

    def __init__(self, state_bus, efficiency_engine, source_root: Path | str):
        super().__init__(state_bus, efficiency_engine)
        self.source_root = Path(source_root)
        db_path = "pforge/var/budget.db"
        budget_meter = BudgetMeter(db_path=db_path)
        self.llm_client = OpenAIClient(budget_meter=budget_meter)

    async def on_tick(self):
        """
        Listens for FixTask commands, applies patches, and verifies them.
        """
        amp_message = await self.state_bus.bus.subscribe("pforge:amp:global:events")

        if amp_message.type == MsgType.FIX_TASK.value:
            logger.info("FixerAgent received a FixTask command.")

            payload = amp_message.payload
            file_path = payload['file_path']
            description = payload['description']
            failed_test_nodeid = payload.get('failed_test_nodeid')

            prompt = (
                f"The file '{file_path}' has a bug.\n"
                f"The bug is described as: {description}\n"
                f"Please provide the complete, corrected content of the file '{file_path}'. "
                "Do not add any explanations or comments, only the raw file content, "
                "enclosed in a single ```python ... ``` block."
            )

            response = await self.llm_client.generate(prompt)
            full_content = response["choices"][0]["message"]["content"]

            if full_content.startswith("```python"):
                full_content = full_content[len("```python"):].strip()
            if full_content.endswith("```"):
                full_content = full_content[:-len("```")].strip()

            with open(file_path, "w") as f:
                f.write(full_content)
            logger.info(f"Applied fix to {file_path}")

            # Invalidate caches to ensure the test runner imports the patched file
            importlib.invalidate_caches()
            time.sleep(1)

            # --- Verification Step ---
            logger.info(f"Verifying fix by running test: {failed_test_nodeid}")
            verification_result = run_tests(
                test_nodes=[failed_test_nodeid] if failed_test_nodeid else [],
                source_root=self.source_root
            )

            fix_is_ok = False
            if verification_result:
                fix_is_ok = verification_result.failed == 0
                tests_summary = {
                    "passed": verification_result.passed,
                    "failed": verification_result.failed,
                    "skipped": verification_result.skipped,
                    "duration_s": verification_result.duration_s,
                    "report_content": verification_result.report_content,
                }
                logger.info(f"Verification result: {'OK' if fix_is_ok else 'FAILED'}")
            else:
                logger.error("Verification test run failed to produce a result.")
                tests_summary = {"error": "Test runner failed"}

            # --- Create Proof Bundle ---
            obligation = ProofObligation(
                id="phi.sem.llm_fix_verified",
                ok=fix_is_ok,
                witness={"prompt": prompt, "response": response}
            )
            proof = ProofBundle(
                tree_sha=verification_result.report_hash if verification_result else "dummy_sha",
                venv_lock_sha="dummy_venv_lock_sha",
                constraints=[obligation],
                tests=tests_summary
            )

            event_type = MsgType.FIX_PATCH_APPLIED.value if fix_is_ok else MsgType.FIX_PATCH_REJECTED.value
            event_payload = {"new_content": full_content, "file_path": file_path}

            await self.send_amp_event(
                event_type=event_type,
                payload=event_payload,
                snap_sha=amp_message.snap_sha,
                proof=proof.model_dump()
            )
            logger.info(f"FixerAgent emitted a {event_type} event for file: {file_path}")
