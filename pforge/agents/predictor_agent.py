from __future__ import annotations
import logging
import numpy as np
from typing import TYPE_CHECKING, Dict

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

        elif msg_type in [MsgType.FIX_PATCH_APPLIED, MsgType.BACKTRACK_COMPLETED]:
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
        """A simple heuristic to infer a source file from a test file path."""
        nodeid = failure.get("nodeid")
        if not nodeid:
            return None

        test_file_path = nodeid.split("::")[0]

        if "tests/unit/" in test_file_path:
            return test_file_path.replace("tests/unit/", "pforge/").replace("test_", "")
        elif "tests/integration/" in test_file_path:
             return test_file_path.replace("tests/integration/", "pforge/").replace("test_", "")
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

        logger.info(f"Assessed risk for failure in '{source_path}'. Effort distribution generated "
                    f"with alpha={alpha}, beta={beta}.")

        analyzed_task_msg = Message(
            type=MsgType.TASK_ANALYZED,
            payload={
                "original_failure": payload,
                "effort_distribution": effort_distribution,
                "inferred_source_path": source_path
            }
        )
        await self.publish(MsgType.TASK_ANALYZED.value, analyzed_task_msg)

    def __del__(self):
        """Ensure the database connection is closed when the agent is destroyed."""
        self.risk_db.close()
