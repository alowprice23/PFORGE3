from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict, List, Any
from dataclasses import dataclass
import uuid
import numpy as np

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.orchestrator.state_bus import StateBus
from pforge.planner.priority import calculate_priority
from pforge.planner.solver_ilp import solve_knapsack_ilp
from pforge.proof.capabilities import issue_token

if TYPE_CHECKING:
    from pforge.config import Config
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.project import Project


logger = logging.getLogger(__name__)

@dataclass
class Task:
    """A generic representation of a task for the planner."""
    id: str
    type: str  # e.g., "fix_bug", "remove_file"
    description: str
    priority: float
    effort: float  # Estimated effort (cost)
    payload: Dict[str, Any]
    retry_count: int = 0
    source_path: str | None = None # The path to the source file to be modified


class PlannerAgent(BaseAgent):
    name = "planner"
    tick_interval: float = 2.0  # Planning is more deliberate

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.state_bus = StateBus(bus)
        self.task_board: Dict[str, Task] = {}
        self.dispatched_tasks: set[str] = set()
        self.conflicted_files: set[str] = set()
        self.effort_budget_per_tick = self.config.planner.effort_budget_per_tick

        # Subscribe to events that can create or resolve tasks
        self.bus.subscribe(self.name, MsgType.METRICS_UPDATED.value)
        self.bus.subscribe(self.name, MsgType.TASK_ANALYZED.value)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_REJECTED.value) # To trigger retries
        self.bus.subscribe(self.name, MsgType.PROPOSE_REMOVAL.value)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)
        self.bus.subscribe(self.name, MsgType.MISFIT_DETECTED.value)
        self.bus.subscribe(self.name, MsgType.CONFLICT_ANALYZED.value)
        self.bus.subscribe(self.name, MsgType.TESTS_PASSED.value)

    async def on_tick(self):
        """
        The main planning loop.
        1. Ingest new information from the message bus to update the task board.
        2. Analyze the current puzzle state and task board.
        3. Select the best tasks to execute based on priority and budget.
        4. Dispatch those tasks to other agents with the necessary capabilities.
        """
        await self._update_task_board()

        if not self.task_board:
            logger.info("Task board is empty. Nothing to plan.")
            return

        tasks_to_dispatch = self._select_tasks_with_ilp()

        if not tasks_to_dispatch:
            logger.info("No tasks selected for dispatch in this cycle.")
            return

        logger.info(f"Dispatching {len(tasks_to_dispatch)} tasks this cycle.")
        for task in tasks_to_dispatch:
            await self._dispatch_task(task)
            self.dispatched_tasks.add(task.id)

    async def _update_task_board(self):
        """Consume messages to add or remove tasks from the board."""
        while True:
            message = await self.bus.get(self.name, timeout=0)
            if not message:
                break

            logger.info(f"PlannerAgent received message: {message.type}")

            if message.type == MsgType.TASK_ANALYZED:
                self._add_fix_tasks_from_analysis(message.payload)
            elif message.type == MsgType.FIX_PATCH_REJECTED:
                self._handle_fix_rejection(message.payload)
            elif message.type == MsgType.PROPOSE_REMOVAL:
                self._add_removal_task(message.payload)
            elif message.type == MsgType.FIX_PATCH_APPLIED:
                self._handle_fix_success(message.payload)
            elif message.type == MsgType.MISFIT_DETECTED:
                self._add_refactor_task_from_misfit(message.payload)
            elif message.type == MsgType.CONFLICT_ANALYZED:
                self.conflicted_files.update(payload.get("minimal_hitting_set", []))
                logger.info(f"Updated conflicted files: {self.conflicted_files}")
            elif message.type == MsgType.TESTS_PASSED:
                self.conflicted_files.clear()
                logger.info("Cleared conflicted files due to successful test run.")

    def _add_fix_tasks_from_analysis(self, payload: dict):
        """Create fix tasks from a TASK_ANALYZED event."""
        original_failure = payload.get("original_failure", {})
        failed_tests = original_failure.get("failed_tests", [])
        effort_dist = payload.get("effort_distribution")
        risk_score = payload.get("risk_score", 0.0)
        source_path = payload.get("inferred_source_path")

        if effort_dist is None:
            logger.error("Received TASK_ANALYZED message without effort distribution.")
            return

        for failure in failed_tests:
            nodeid = failure.get("nodeid")
            if not nodeid or nodeid in self.dispatched_tasks:
                continue

            impact = 1.0
            frequency = 1.0
            in_conflict = source_path in self.conflicted_files if source_path else False
            priority = calculate_priority(
                impact, frequency, effort_dist, risk_score=risk_score, in_conflict=in_conflict
            )

            task = Task(
                id=nodeid,
                type="fix_bug",
                description=f"Fix the bug causing test '{nodeid}' to fail.",
                priority=priority,
                effort=effort_dist.mean(),
                payload=failure,  # The payload is the original failure dict
                retry_count=0,
                source_path=source_path,
            )
            self.task_board[task.id] = task
            logger.info(f"Added new fix task to board: {task.id} with priority {priority:.2f}")

    def _handle_fix_rejection(self, payload: dict):
        """Handles a rejected fix by requeueing the task for a retry."""
        nodeid = payload.get("failed_test_nodeid")
        if not nodeid:
            logger.warning("FIX_PATCH_REJECTED message received without a failed_test_nodeid.")
            return

        # Mark the task as available for dispatch again
        self.dispatched_tasks.discard(nodeid)

        original_task = self.task_board.get(nodeid)
        if not original_task:
            logger.warning(f"Could not find original task for failed nodeid: {nodeid}")
            return

        # --- Create a new retry task ---
        retry_count = original_task.retry_count + 1

        # Increase priority and effort for retries
        new_priority = original_task.priority * 1.5
        new_effort = original_task.effort * 1.2

        # The payload for the new task should include info about the failed fix
        new_payload = original_task.payload.copy()
        new_payload["failed_fix_info"] = payload

        retry_task = Task(
            id=original_task.id,
            type="fix_bug",
            description=f"[Retry {retry_count}] " + original_task.description,
            priority=new_priority,
            effort=new_effort,
            payload=new_payload,
            retry_count=retry_count,
        )

        self.task_board[retry_task.id] = retry_task
        logger.info(f"Re-queued task {retry_task.id} for retry with new priority {new_priority:.2f}")

    def _handle_fix_success(self, payload: dict):
        """Handles a successful fix by removing the task from the board."""
        op_id = payload.get("op_id")
        if not op_id:
            return

        # This is inefficient, but OK for now. A real system would have better state management.
        task_id_to_remove = None
        for task in self.task_board.values():
            # The op_id is added to the payload during dispatch
            if task.payload.get("op_id") == op_id:
                task_id_to_remove = task.id
                break

        if task_id_to_remove in self.task_board:
            del self.task_board[task_id_to_remove]
            self.dispatched_tasks.discard(task_id_to_remove)
            logger.info(f"Task {task_id_to_remove} completed and removed from board.")

    def _add_removal_task(self, payload: dict):
        """Create a removal task from a PROPOSE_REMOVAL event."""
        file_path = payload.get("file_path")
        if not file_path or file_path in self.dispatched_tasks:
            return

        # Placeholder values
        impact = 0.5 # Lower impact than fixing a bug
        frequency = 1.0
        effort_dist = np.array([1.0]) # Simple deletion is low effort

        in_conflict = file_path in self.conflicted_files
        priority = calculate_priority(
            impact, frequency, effort_dist, in_conflict=in_conflict
        )

        task = Task(
            id=file_path, # Use file path as unique ID
            type="remove_file",
            description=f"Remove unused file '{file_path}'.",
            priority=priority,
            effort=1.0,
            payload=payload,
        )
        self.task_board[task.id] = task
        logger.info(f"Added new removal task to board: {task.id} with priority {priority:.2f}")

    def _add_refactor_task_from_misfit(self, payload: dict):
        """Create a refactoring task from a MISFIT_DETECTED event."""
        file_path = payload.get("file_path")
        symbol = payload.get("symbol")
        suggestion = payload.get("suggestion")
        task_id = f"refactor:{file_path}:{symbol}"

        if not all([file_path, symbol, suggestion]) or task_id in self.dispatched_tasks:
            return

        # Refactoring is generally lower impact than fixing a failing test
        impact = 0.4
        frequency = 1.0
        # Effort for refactoring is higher than simple deletion
        effort_dist = np.array([3.0, 4.0, 5.0])

        in_conflict = file_path in self.conflicted_files
        priority = calculate_priority(
            impact, frequency, effort_dist, in_conflict=in_conflict
        )

        task = Task(
            id=task_id,
            type="refactor_code",
            description=f"Refactor: Move '{symbol}' from '{file_path}' to '{suggestion}'.",
            priority=priority,
            effort=effort_dist.mean(),
            payload=payload,
        )
        self.task_board[task.id] = task
        logger.info(f"Added new refactor task to board: {task.id} with priority {priority:.2f}")

    def _select_tasks_with_ilp(self) -> List[Task]:
        """
        Selects the best tasks to dispatch using an ILP knapsack solver.
        """
        candidate_tasks = [t for t in self.task_board.values() if t.id not in self.dispatched_tasks]
        if not candidate_tasks:
            return []

        items_for_solver = [
            {"name": task.id, "priority": task.priority, "cost": task.effort}
            for task in candidate_tasks
        ]

        selected_items = solve_knapsack_ilp(items_for_solver, self.effort_budget_per_tick)

        if selected_items is None:
            logger.warning("ILP solver is not available or failed. Falling back to greedy.")
            # Fallback to greedy can be implemented here if needed. For now, return empty.
            return []

        selected_task_ids = {item['name'] for item in selected_items}
        return [task for task in candidate_tasks if task.id in selected_task_ids]

    async def _dispatch_task(self, task: Task):
        """Dispatches a single task to the appropriate agent with a capability token."""
        op_id = str(uuid.uuid4())

        if task.type == "fix_bug":
            task.payload["op_id"] = op_id
            fix_payload = {
                "op_id": op_id,
                "file_path": task.source_path,
                "description": task.description + f"\n\nTraceback:\n{task.payload.get('traceback','')}",
                "failed_test_nodeid": task.id,
            }
            if "failed_fix_info" in task.payload:
                fix_payload["failed_fix_info"] = task.payload["failed_fix_info"]

            # Grant the FixerAgent the capability to write to this file and run tests
            token = issue_token(actor="fixer", scope=["fs:write", "exec:test"], op_id=op_id)
            fix_payload["capability_token"] = token

            message = Message(type=MsgType.FIX_TASK, payload=fix_payload)
            await self.publish(MsgType.FIX_TASK.value, message)
            logger.info(f"Dispatched FIX_TASK for {task.source_path} with op_id {op_id}")

        elif task.type == "remove_file":
            removal_payload = {
                "op_id": op_id,
                "file_path": task.payload.get("file_path"),
            }
            # Grant the FalsePieceAgent the capability to delete this file
            token = issue_token(actor="false_piece", scope=["fs:delete"], op_id=op_id)
            removal_payload["capability_token"] = token

            message = Message(type=MsgType.ACCEPT_REMOVAL, payload=removal_payload)
            await self.publish(MsgType.ACCEPT_REMOVAL.value, message)
            logger.info(f"Dispatched ACCEPT_REMOVAL for {removal_payload['file_path']} with op_id {op_id}")

        elif task.type == "refactor_code":
            refactor_payload = {
                "op_id": op_id,
                "file_path": task.payload.get("file_path"),
                "symbol": task.payload.get("symbol"),
                "suggestion": task.payload.get("suggestion"),
                "description": task.description,
            }
            # Grant the FixerAgent the capability to write to multiple files and run tests
            token = issue_token(actor="fixer", scope=["fs:write", "fs:delete", "exec:test"], op_id=op_id)
            refactor_payload["capability_token"] = token

            message = Message(type=MsgType.REFACTOR_TASK, payload=refactor_payload)
            await self.publish(MsgType.REFACTOR_TASK.value, message)
            logger.info(f"Dispatched REFACTOR_TASK for '{refactor_payload['symbol']}' with op_id {op_id}")
