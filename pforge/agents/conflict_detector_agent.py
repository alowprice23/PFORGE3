from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict, Set, List

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.tools.ast_utils import find_modified_symbols

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
        # Stores which op_id corresponds to which file and content.
        self.active_patches: Dict[str, dict] = {} # op_id -> {file_path: str, content: str, original_content: str}

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
            content = payload.get("content")
            original_content = payload.get("original_content")

            if op_id and file_path and content and original_content:
                self.active_patches[op_id] = {
                    "file_path": file_path,
                    "content": content,
                    "original_content": original_content,
                }
                logger.info(f"Tracking active patch: op_id={op_id} for file={file_path}")

        elif msg_type == MsgType.TESTS_PASSED:
            self._reset_state()

        elif msg_type == MsgType.SPEC_CHECKED and not payload.get("is_valid"):
            failed_op_id = payload.get("op_id")
            if not failed_op_id or failed_op_id not in self.active_patches:
                return

            logger.info(f"Spec check failed for op_id: {failed_op_id}. Analyzing for semantic conflicts.")

            failed_patch = self.active_patches[failed_op_id]
            failed_file = failed_patch["file_path"]

            try:
                modified_symbols_a = find_modified_symbols(
                    failed_patch["original_content"], failed_patch["content"]
                )
            except Exception as e:
                logger.error(f"Could not parse AST for failed patch {failed_op_id}: {e}")
                return

            if not modified_symbols_a:
                logger.warning(f"No modified symbols found for failed patch {failed_op_id}. Cannot determine conflict.")
                return

            logger.info(f"Op {failed_op_id} modified symbols: {modified_symbols_a} in {failed_file}")

            # Find other patches that modify the same file and the same symbols.
            for other_op_id, other_patch in self.active_patches.items():
                if other_op_id == failed_op_id or other_patch["file_path"] != failed_file:
                    continue

                try:
                    modified_symbols_b = find_modified_symbols(
                        other_patch["original_content"], other_patch["content"]
                    )
                except Exception as e:
                    logger.error(f"Could not parse AST for other patch {other_op_id}: {e}")
                    continue

                logger.info(f"Op {other_op_id} modified symbols: {modified_symbols_b} in {failed_file}")

                # If the intersection of modified symbols is not empty, we have a conflict.
                if modified_symbols_a.intersection(modified_symbols_b):
                    conflict_set = {failed_op_id, other_op_id}
                    # Use a sorted tuple for a canonical key
                    conflict_key = ":".join(sorted(list(conflict_set)))

                    if conflict_key not in self.conflict_sets:
                        self.conflict_sets[conflict_key] = conflict_set
                        logger.info(f"Found semantic conflict between {failed_op_id} and {other_op_id} on symbols "
                                    f"{modified_symbols_a.intersection(modified_symbols_b)}. Adding conflict set: {conflict_set}")
                        await self._compute_and_publish_hitting_set()


    async def _compute_and_publish_hitting_set(self):
        if not self.conflict_sets:
            return

        uncovered_sets = list(self.conflict_sets.values())
        hitting_set = set()

        while uncovered_sets:
            # Find the element that appears in the most uncovered sets
            element_counts = {}
            for s in uncovered_sets:
                for element in s:
                    if element not in hitting_set:
                        element_counts[element] = element_counts.get(element, 0) + 1

            if not element_counts:
                break

            best_element = max(element_counts, key=element_counts.get)
            hitting_set.add(best_element)

            # Remove sets covered by the new element
            uncovered_sets = [s for s in uncovered_sets if best_element not in s]

        if hitting_set:
            files_to_revert = {self.active_patches[op_id]["file_path"] for op_id in hitting_set if op_id in self.active_patches}

            if not files_to_revert:
                 logger.error("Computed a hitting set of ops, but could not map them back to files.")
                 return

            logger.info(f"Computed hitting set of files to revert: {files_to_revert}")

            analysis_message = Message(
                type=MsgType.CONFLICT_ANALYZED,
                payload={"minimal_hitting_set": list(files_to_revert)}
            )
            await self.publish(MsgType.CONFLICT_ANALYZED.value, analysis_message)
        else:
            logger.warning("Could not compute a hitting set.")
