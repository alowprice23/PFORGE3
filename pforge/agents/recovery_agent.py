from __future__ import annotations
import logging
import importlib
import time
import uuid
from typing import TYPE_CHECKING, List, Tuple, Callable, Dict, Any

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.proof.capabilities import issue_token

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config, RecoveryCheck
    from pforge.project import Project

logger = logging.getLogger(__name__)

# A type hint for a detector function
DetectorFunc = Callable[[], Tuple[bool, Dict[str, Any]]]
# A type hint for an action function
ActionFunc = Callable[[], Dict[str, Any]]

class RecoveryAgent(BaseAgent):
    """
    Periodically runs health checks on the environment and attempts to
    perform recovery actions if any checks fail. The checks are loaded
    dynamically from the project configuration.
    """
    name = "recovery"
    tick_interval: float = 60.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.recovery_config = self.config.recovery
        self.health_checks: List[Tuple[DetectorFunc, ActionFunc]] = []

    async def on_startup(self):
        """
        On startup, load the health checks from the config, but only if the
        agent has the required capability.
        """
        # For simulation, we grant the token directly. In a real system,
        # this would be provided securely at startup.
        startup_op_id = f"recovery_startup_{int(time.time())}"
        token = issue_token(self.name, ["system:load_dynamic_modules"], startup_op_id)
        self.receive_token(token, startup_op_id)

        if await self.has_capability("system:load_dynamic_modules", startup_op_id):
            logger.info("RecoveryAgent has 'system:load_dynamic_modules' capability. Loading health checks.")
            self.health_checks = self._load_health_checks()
        else:
            logger.error("RecoveryAgent lacks 'system:load_dynamic_modules' capability. No health checks will be loaded.")

    def _load_health_checks(self) -> List[Tuple[DetectorFunc, ActionFunc]]:
        """Dynamically loads detector and action functions from config."""
        checks = []
        if not self.recovery_config.enabled:
            return checks

        for check_config in self.recovery_config.checks:
            try:
                detector_module_path, detector_func_name = check_config.detector.rsplit('.', 1)
                action_module_path, action_func_name = check_config.action.rsplit('.', 1)

                detector_module = importlib.import_module(detector_module_path)
                action_module = importlib.import_module(action_module_path)

                detector_func = getattr(detector_module, detector_func_name)
                action_func = getattr(action_module, action_func_name)

                checks.append((detector_func, action_func))
                logger.info(f"Successfully loaded health check: {check_config.detector}")
            except (ImportError, AttributeError, ValueError) as e:
                logger.error(f"Failed to load health check '{check_config.detector}': {e}")

        return checks

    async def on_tick(self):
        """
        Iterates through all registered health checks, running detectors and
        triggering actions for any failures.
        """
        if not self.health_checks:
            return

        logger.info("RecoveryAgent running periodic health checks...")
        for detector, action in self.health_checks:
            try:
                is_ok, details = detector()
                if not is_ok:
                    logger.warning(f"Health check '{detector.__name__}' failed. Details: {details}")
                    await self._run_recovery_action(action, details)
            except Exception as e:
                logger.error(f"Error running detector '{detector.__name__}': {e}")

    async def _run_recovery_action(self, action: ActionFunc, failure_details: Dict[str, Any]):
        """
        Executes a recovery action and publishes the result, guarded by a capability check.
        """
        op_id = f"recovery_action_{action.__name__}_{uuid.uuid4()}"

        # In a real system, the orchestrator/planner would grant this token
        # based on the detected failure. For this simulation, we grant it directly.
        # A more granular capability like f"exec:{action.__name__}" could be used.
        token = issue_token(self.name, ["exec:recovery_action"], op_id)
        self.receive_token(token, op_id)

        if not await self.has_capability("exec:recovery_action", op_id):
            logger.error(f"Attempted to run recovery action '{action.__name__}' without 'exec:recovery_action' capability for op_id {op_id}.")
            return

        logger.info(f"Executing recovery action '{action.__name__}'...")
        try:
            action_proof = action()
            logger.info(f"Recovery action '{action.__name__}' completed. Proof: {action_proof}")

            # Publish a message indicating what action was taken
            recovery_message = Message(
                type=MsgType.RECOVERY_ACTION_TAKEN,
                payload={
                    "action_name": action.__name__,
                    "failure_details": failure_details,
                    "action_proof": action_proof,
                }
            )
            await self.publish(MsgType.RECOVERY_ACTION_TAKEN.value, recovery_message)

        except Exception as e:
            logger.error(f"Error executing recovery action '{action.__name__}': {e}")
