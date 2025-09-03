from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict, Set, List

from pysat.examples.hitman import Hitman

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class ConflictDetectorAgent(BaseAgent):
    """
    Analyzes specification failures to build a conflict hypergraph of edit
    operations (op_ids) and computes the minimal set of ops to revert.
    """
    name: str = "conflict_detector"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.SPEC_CHECKED.value)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)
        self.bus.subscribe(self.name, MsgType.TESTS_PASSED.value)

        # Stores the sets of op_ids that fail a spec check together.
        self.conflict_sets: Dict[str, Set[str]] = {}
        # Stores which op_id corresponds to which file.
        self.active_patches: Dict[str, str] = {} # op_id -> file_path

    def _reset_state(self):
        """Resets the conflict detection state."""
        logger.info("Resetting conflict detector state due to successful tests.")
        self.conflict_sets = {}
        self.active_patches = {}

    async def on_tick(self):
        message = await self.bus.get(self.name, timeout=0.1)
        if not message:
            return

        msg_type = message.type
        payload = message.payload

        if msg_type == MsgType.FIX_PATCH_APPLIED:
            op_id = payload.get("op_id")
            file_path = payload.get("file_path")
            if op_id and file_path:
                self.active_patches[op_id] = file_path
                logger.info(f"Tracking active patch: op_id={op_id} for file={file_path}")

        elif msg_type == MsgType.TESTS_PASSED:
            self._reset_state()

        elif msg_type == MsgType.SPEC_CHECKED and not payload.get("is_valid"):
            op_id = payload.get("op_id")
            if not op_id:
                return

            # A spec check failed for the file modified by op_id.
            # The conflict set is this op_id plus all other active op_ids.
            # This assumes any active patch could be in conflict.
            conflict_set = set(self.active_patches.keys())

            if not conflict_set:
                logger.warning("Spec check failed, but no active patches to blame.")
                return

            check_name = payload.get("checks", [{}])[0].get("check", "unknown")
            failed_file = payload.get("file_path")
            conflict_key = f"{check_name}:{failed_file}:{op_id}"

            if conflict_key not in self.conflict_sets:
                self.conflict_sets[conflict_key] = conflict_set
                logger.info(f"Added conflict set '{conflict_key}' with op_ids: {conflict_set}")
                await self._compute_and_publish_hitting_set()

    async def _compute_and_publish_hitting_set(self):
        if not self.conflict_sets:
            return

        hyperedges: List[List[str]] = [list(s) for s in self.conflict_sets.values()]

        with Hitman(bootstrap_with=hyperedges, htype='sorted') as h:
            # We want the minimal set of op_ids to revert.
            minimal_hitting_set_ops = h.get()

        if minimal_hitting_set_ops:
            # The backtracker needs file paths, not op_ids.
            files_to_revert = {self.active_patches[op_id] for op_id in minimal_hitting_set_ops if op_id in self.active_patches}

            if not files_to_revert:
                 logger.error("Computed a hitting set of ops, but could not map them back to files.")
                 return

            logger.info(f"Computed minimal hitting set of files to revert: {files_to_revert}")

            analysis_message = Message(
                type=MsgType.CONFLICT_ANALYZED,
                payload={"minimal_hitting_set": list(files_to_revert)}
            )
            await self.publish(MsgType.CONFLICT_ANALYZED.value, analysis_message)
        else:
            logger.warning("Could not compute a minimal hitting set.")
