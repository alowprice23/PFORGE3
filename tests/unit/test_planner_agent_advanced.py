from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from pforge.agents.planner_agent import PlannerAgent, Task
from pforge.orchestrator.signals import Message, MsgType
from pforge.orchestrator.state_bus import PuzzleState


@pytest.fixture
def mock_bus():
    bus = MagicMock()
    bus.get = AsyncMock()
    bus.publish = AsyncMock()
    return bus

@pytest.fixture
def mock_config():
    return MagicMock()

@pytest.fixture
def test_agent(mock_bus, mock_config):
    project = MagicMock()
    agent = PlannerAgent(bus=mock_bus, config=mock_config, project=project)
    agent.state_bus = MagicMock()
    agent.state_bus.get_snapshot.return_value = PuzzleState()
    # Mock the priority calculation to be predictable
    with patch('pforge.agents.planner_agent.calculate_priority') as mock_calc:
        # Make priority directly proportional to impact
        mock_calc.side_effect = lambda impact, freq, eff: impact
        yield agent

@pytest.mark.asyncio
async def test_planner_creates_tasks_from_events(test_agent, mock_bus):
    # Prepare messages to be on the bus
    task_analyzed_msg = Message(
        type=MsgType.TASK_ANALYZED,
        payload={
            "original_failure": {
                "failed_tests": [{"nodeid": "tests/test_a.py::test_one", "traceback": "..."}]
            },
            "effort_distribution": np.array([1.5, 2.0, 2.5])
        }
    )
    propose_removal_msg = Message(
        type=MsgType.PROPOSE_REMOVAL,
        payload={"file_path": "pforge/legacy/old_util.py"}
    )
    mock_bus.get.side_effect = [task_analyzed_msg, propose_removal_msg, None]

    # Run the update logic
    await test_agent._update_task_board()

    # Assert task board is populated correctly
    assert len(test_agent.task_board) == 2
    assert "tests/test_a.py::test_one" in test_agent.task_board
    assert "pforge/legacy/old_util.py" in test_agent.task_board
    assert test_agent.task_board["tests/test_a.py::test_one"].type == "fix_bug"
    assert test_agent.task_board["pforge/legacy/old_util.py"].type == "remove_file"

@pytest.mark.asyncio
async def test_planner_knapsack_selection(test_agent):
    # Manually create tasks with different priorities and efforts
    test_agent.task_board = {
        "task1": Task(id="task1", type="fix_bug", description="", priority=10.0, effort=8.0, payload={}),
        "task2": Task(id="task2", type="fix_bug", description="", priority=8.0, effort=5.0, payload={}),
        "task3": Task(id="task3", type="remove_file", description="", priority=3.0, effort=2.0, payload={}),
    }
    test_agent.effort_budget_per_tick = 10.0

    selected_tasks = test_agent._select_tasks_with_knapsack()

    # Greedy choice is based on priority/effort ratio:
    # task1: 10/8 = 1.25
    # task2: 8/5 = 1.6
    # task3: 3/2 = 1.5
    # So, order should be task2, task3, task1.
    # With a budget of 10, it should select task2 (cost 5) and task3 (cost 2).
    # Total effort = 7 <= 10.

    assert len(selected_tasks) == 2
    selected_ids = {t.id for t in selected_tasks}
    assert "task2" in selected_ids
    assert "task3" in selected_ids

@pytest.mark.asyncio
async def test_planner_dispatches_task_with_token(test_agent, mock_bus):
    # Create a single high-priority task
    fix_task = Task(
        id="task1", type="fix_bug", description="A bug", priority=10.0, effort=5.0,
        payload={"nodeid": "tests/test_b.py::test_two", "traceback": "Error"}
    )

    # Add the task to the board so the initial check doesn't fail
    test_agent.task_board[fix_task.id] = fix_task

    # Mock the knapsack to return this one task
    with patch.object(test_agent, '_select_tasks_with_knapsack', return_value=[fix_task]):
        # Mock the update task board to do nothing
        with patch.object(test_agent, '_update_task_board', new_callable=AsyncMock):
            await test_agent.on_tick()

    # Assert that a FIX_TASK message was published
    mock_bus.publish.assert_called_once()
    published_message = mock_bus.publish.call_args[0][1]
    assert published_message.type == MsgType.FIX_TASK

    # Assert the payload contains a capability token
    payload = published_message.payload
    assert "capability_token" in payload
    assert isinstance(payload["capability_token"], str)
    assert payload["op_id"] is not None
    assert payload["file_path"] is not None
