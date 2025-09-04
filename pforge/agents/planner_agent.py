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


class PlannerAgent(BaseAgent):
    name = "planner"
    tick_interval: float = 2.0  # Planning is more deliberate

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.state_bus = StateBus(bus)
        self.task_board: Dict[str, Task] = {}
        self.dispatched_tasks: set[str] = set()
        self.effort_budget_per_tick = 10.0 # An arbitrary budget

        # Subscribe to events that can create or resolve tasks
        self.bus.subscribe(self.name, MsgType.METRICS_UPDATED.value)
        self.bus.subscribe(self.name, MsgType.TASK_ANALYZED.value) # To get failure details and risk assessment
        self.bus.subscribe(self.name, MsgType.FIX_FAILED.value) # To trigger retries
        self.bus.subscribe(self.name, MsgType.PROPOSE_REMOVAL.value)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value) # To clear completed tasks

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

        tasks_to_dispatch = self._select_tasks_with_knapsack()

        if not tasks_to_dispatch:
            logger.info("No tasks selected for dispatch in this cycle.")
            return

        logger.info(f"Dispatching {len(tasks_to_dispatch)} tasks this cycle.")
        for task in tasks_to_dispatch:
            await self._dispatch_task(task)
            self.dispatched_tasks.add(task.id) # Mark as dispatched

    async def _update_task_board(self):
        """Consume messages to add or remove tasks from the board."""
        # This is a simplified version; a real implementation would use a more robust queue
        # and handle more message types.
        while True:
            message = await self.bus.get(self.name, timeout=0)
            if not message:
                break

            logger.info(f"PlannerAgent received message: {message.type}")

            if message.type == MsgType.TASK_ANALYZED:
                self._add_fix_tasks_from_analysis(message.payload)
            elif message.type == MsgType.FIX_FAILED:
                # Remove the task from dispatched so it can be retried
                nodeid = message.payload.get("failed_test_nodeid")
                if nodeid in self.dispatched_tasks:
                    self.dispatched_tasks.discard(nodeid)
                self._add_fix_tasks_from_failure(message.payload)
            elif message.type == MsgType.PROPOSE_REMOVAL:
                self._add_removal_task(message.payload)
            elif message.type == MsgType.FIX_PATCH_APPLIED:
                # The orchestrator will handle task completion
                pass

    def _add_fix_tasks_from_analysis(self, payload: dict):
        """Create fix tasks from a TASK_ANALYZED event."""
        original_failure = payload.get("original_failure", {})
        failed_tests = original_failure.get("failed_tests", [])
        effort_dist = payload.get("effort_distribution")

        if effort_dist is None:
            logger.error("Received TASK_ANALYZED message without effort distribution.")
            return

        for failure in failed_tests:
            nodeid = failure.get("nodeid")
            if not nodeid or nodeid in self.dispatched_tasks:
                continue # Skip if no ID or already dispatched

            # Use real data from the PredictorAgent
            impact = 1.0  # Placeholder
            frequency = 1.0 # Placeholder

            priority = calculate_priority(impact, frequency, effort_dist)

            task = Task(
                id=nodeid, # Use test nodeid as a unique task ID
                type="fix_bug",
                description=f"Fix the bug causing test '{nodeid}' to fail.",
                priority=priority,
                effort=effort_dist.mean(),
                # Pass the original failure payload to the dispatcher
                payload=failure,
            )
            self.task_board[task.id] = task
            logger.info(f"Added new fix task to board: {task.id} with priority {priority:.2f}")

    def _add_fix_tasks_from_failure(self, payload: dict):
        """Create a fix task from a FIX_FAILED event."""
        op_id = payload.get("op_id")
        if not op_id:
            logger.warning("FIX_FAILED message received without an op_id.")
            return

        # Find the original task by op_id
        original_task = None
        for task in self.task_board.values():
            if task.payload.get("op_id") == op_id:
                original_task = task
                break

        if not original_task:
            logger.warning(f"Could not find original task for op_id: {op_id}")
            return

        nodeid = original_task.id

        # For a retry, we can assume the effort is high and the impact is high.
        impact = 1.0
        frequency = 1.0
        effort_dist = np.array([10.0]) # High effort for a retry

        priority = calculate_priority(impact, frequency, effort_dist)

        task = Task(
            id=nodeid,
            type="fix_bug",
            description=payload.get("description", ""),
            priority=priority,
            effort=10.0,
            payload=payload,
        )
        self.task_board[task.id] = task
        logger.info(f"Added new retry fix task to board: {task.id} with priority {priority:.2f}")

    def _add_removal_task(self, payload: dict):
        """Create a removal task from a PROPOSE_REMOVAL event."""
        file_path = payload.get("file_path")
        if not file_path or file_path in self.dispatched_tasks:
            return

        # Placeholder values
        impact = 0.5 # Lower impact than fixing a bug
        frequency = 1.0
        effort_dist = np.array([1.0]) # Simple deletion is low effort

        priority = calculate_priority(impact, frequency, effort_dist)

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

    def _select_tasks_with_knapsack(self) -> List[Task]:
        """
        Selects the best tasks to dispatch using a greedy knapsack algorithm.
        This is a classic 0/1 knapsack problem: maximize total priority given a budget of effort.
        """
        # Filter out already dispatched tasks
        candidate_tasks = [t for t in self.task_board.values() if t.id not in self.dispatched_tasks]

        if not candidate_tasks:
            return []

        # Sort tasks by priority-to-effort ratio (the greedy choice)
        candidate_tasks.sort(key=lambda t: t.priority / t.effort, reverse=True)

        selected_tasks = []
        current_effort = 0
        for task in candidate_tasks:
            if current_effort + task.effort <= self.effort_budget_per_tick:
                selected_tasks.append(task)
                current_effort += task.effort

        return selected_tasks

    async def _dispatch_task(self, task: Task):
        """Dispatches a single task to the appropriate agent with a capability token."""
        op_id = str(uuid.uuid4())

        if task.type == "fix_bug":
            task.payload["op_id"] = op_id
            # This logic is adapted from the old PlannerAgent
            nodeid = task.payload.get("nodeid")
            test_file_path = nodeid.split("::")[0]
            # This inference logic should be improved or replaced
            inferred_source_path = test_file_path.replace("tests/", "pforge/").replace("test_", "")

            fix_payload = {
                "op_id": op_id,
                "file_path": inferred_source_path,
                "description": task.description + f"\n\nTraceback:\n{task.payload.get('traceback','')}",
                "failed_test_nodeid": nodeid,
            }
            # Grant the FixerAgent the capability to write to this file and run tests
            token = issue_token(actor="fixer", scope=["fs:write", "exec:test"], op_id=op_id)
            fix_payload["capability_token"] = token

            message = Message(type=MsgType.FIX_TASK, payload=fix_payload)
            await self.publish(MsgType.FIX_TASK.value, message)
            logger.info(f"Dispatched FIX_TASK for {inferred_source_path} with op_id {op_id}")

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
