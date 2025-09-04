from __future__ import annotations
import logging
import numpy as np
from typing import TYPE_CHECKING, Dict
import os
import glob
from pathlib import Path

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.storage.risk_model_db import RiskModelDB

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class PredictorAgent(BaseAgent):
    """
    Models the risk of editing files and provides risk-adjusted effort
    estimates to the planner. It uses a Bayesian model to learn from
    past successes and failures, stored in a SQLite database.
    """
    name = "predictor"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.TESTS_FAILED.value)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_REJECTED.value)
        self.bus.subscribe(self.name, MsgType.BACKTRACK_COMPLETED.value)

        self.risk_db = RiskModelDB()

    async def on_tick(self):
        """
        Consumes events to update the risk model and to assess new tasks.
        """
        message = await self.bus.get(self.name, timeout=0.1)
        if not message:
            return

        msg_type = message.type
        payload = message.payload

        if msg_type == MsgType.TESTS_FAILED:
            logger.info("PredictorAgent consumed TESTS_FAILED event. Assessing risk.")
            await self._handle_failure_and_assess_risk(payload)

        elif msg_type in [MsgType.FIX_PATCH_APPLIED, MsgType.FIX_PATCH_REJECTED, MsgType.BACKTRACK_COMPLETED]:
            # The op_id is now the key to finding the file path for the update
            op_id = payload.get("op_id")
            if op_id:
                # This assumes another agent is tracking which file belongs to which op_id.
                # For now, we'll assume the file_path is still in the payload.
                file_path = payload.get("file_path")
                if file_path:
                    success = msg_type == MsgType.FIX_PATCH_APPLIED
                    self.risk_db.update_risk_params(file_path, success=success)
                    logger.info(f"Updated risk for {file_path} (success={success})")

    def _infer_source_path_from_test_failure(self, failure: Dict) -> str | None:
        """
        Infers a source file from a test file path using a filename-based search.
        e.g., `tests/unit/test_foo.py` -> `pforge/foo.py`
        """
        nodeid = failure.get("nodeid")
        if not nodeid:
            logger.warning("Cannot infer source path: failure has no 'nodeid'.")
            return None

        test_file_path_str = nodeid.split("::")[0]
        test_filename = Path(test_file_path_str).name

        if not test_filename.startswith("test_") or not test_filename.endswith(".py"):
            logger.warning(f"Cannot infer source path: test filename '{test_filename}' does not follow 'test_*.py' pattern.")
            return None

        source_filename = test_filename[5:]  # "test_foo.py" -> "foo.py"

        # In the test environment, the project root can be a symlink.
        # We need to resolve it to a real path for glob and other fs operations to work reliably.
        project_real_path = self.project.root.resolve()

        # Search for the source file using glob, which is robust to directory structures.
        search_pattern = str(project_real_path / '**' / source_filename)
        found_files = glob.glob(search_pattern, recursive=True)

        if not found_files:
            logger.warning(f"Could not find a matching source file for '{source_filename}' using glob in '{project_real_path}'")
            return None

        # Filter out test files and return the first valid source file found.
        for file_path_str in found_files:
            file_path = Path(file_path_str)

            # Use the real project path for relativity check
            relative_path = file_path.relative_to(project_real_path)

            if "tests" not in str(relative_path):
                logger.info(f"Inferred source path '{relative_path}' from test '{test_file_path_str}'")
                # Return the original-style relative path, not the resolved one
                return str(file_path.relative_to(self.project.root))

        logger.warning(f"Found potential matches for '{source_filename}' but all were in a 'tests' directory: {found_files}")
        return None

    async def _handle_failure_and_assess_risk(self, payload: dict):
        failed_tests = payload.get("failed_tests", [])
        if not failed_tests:
            return

        source_path = self._infer_source_path_from_test_failure(failed_tests[0])

        if not source_path:
            logger.warning(f"Could not infer source path for failure: {failed_tests[0].get('nodeid')}")
            # Get default risk if we can't determine the file
            params = {"alpha": RiskModelDB.DEFAULT_ALPHA, "beta": RiskModelDB.DEFAULT_BETA}
        else:
            params = self.risk_db.get_risk_params(source_path)

        alpha = params["alpha"]
        beta = params["beta"]

        effort_distribution = np.random.gamma(shape=alpha, scale=1/beta, size=100)
        risk_score = alpha / (alpha + beta)

        logger.info(f"Assessed risk for failure in '{source_path}'. Effort distribution generated "
                    f"with alpha={alpha}, beta={beta}. Calculated risk score: {risk_score:.2f}")

        analyzed_task_msg = Message(
            type=MsgType.TASK_ANALYZED,
            payload={
                "original_failure": payload,
                "effort_distribution": effort_distribution,
                "inferred_source_path": source_path,
                "risk_score": risk_score,
            }
        )
        await self.publish(MsgType.TASK_ANALYZED.value, analyzed_task_msg)

    def __del__(self):
        """Ensure the database connection is closed when the agent is destroyed."""
        self.risk_db.close()
