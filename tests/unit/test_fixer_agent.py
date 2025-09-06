from __future__ import annotations
from unittest.mock import MagicMock, AsyncMock

import pytest

from pforge.agents.fixer_agent import FixerAgent
from pforge.orchestrator.signals import Message, MsgType


@pytest.fixture
def mock_dependencies():
    """Provides a dictionary of mocked dependencies for the FixerAgent."""
    bus_mock = MagicMock()
    bus_mock.get = AsyncMock()
    return {
        "bus": bus_mock,
        "config": MagicMock(),
        "project": MagicMock(),
        "llm_client": MagicMock(),
        "dep_graph": MagicMock(),
        "coverage_index": MagicMock(),
        "test_selector": MagicMock(),
        "test_runner": MagicMock(),
    }


@pytest.mark.asyncio
async def test_fixer_agent_handles_fix_task(mock_dependencies):
    """
    Tests that the FixerAgent correctly processes a FIX_TASK message.
    """
    # Arrange
    agent = FixerAgent(**mock_dependencies)

    # Mock the bus to return a FIX_TASK message
    fix_task_payload = {
        "file_path": "test.py",
        "description": "A bug",
        "op_id": "test_op_123",
        "capability_token": "dummy_token",
        "failed_test_nodeid": "tests/test_dummy.py::test_fail"
    }
    fix_task_message = Message(type=MsgType.FIX_TASK, payload=fix_task_payload)

    # Since get is an AsyncMock, we set the return value like this
    mock_dependencies["bus"].get.return_value = fix_task_message

    # Mock the agent's internal methods that will be called
    agent._handle_fix_task = AsyncMock()

    # Act
    await agent.on_tick()

    # Assert
    mock_dependencies["bus"].get.assert_called_once_with(agent.name)
    agent._handle_fix_task.assert_called_once_with(fix_task_payload)
