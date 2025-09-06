from __future__ import annotations
from unittest.mock import MagicMock, AsyncMock

import pytest

from pforge.agents.false_piece_agent import FalsePieceAgent
from pforge.orchestrator.signals import Message, MsgType


@pytest.fixture
def mock_dependencies():
    """Provides a dictionary of mocked dependencies for the FalsePieceAgent."""
    bus_mock = MagicMock()
    bus_mock.get = AsyncMock()
    return {
        "bus": bus_mock,
        "config": MagicMock(),
        "project": MagicMock(),
        "llm_client": MagicMock(),
        "dep_graph": MagicMock(),
    }


@pytest.mark.asyncio
async def test_false_piece_agent_handles_accept_removal(mock_dependencies):
    """
    Tests that the FalsePieceAgent correctly processes an ACCEPT_REMOVAL message.
    """
    # Arrange
    agent = FalsePieceAgent(**mock_dependencies)

    # Mock the bus to return an ACCEPT_REMOVAL message
    removal_payload = {
        "file_path": "test.py",
        "op_id": "test_op_123",
        "capability_token": "dummy_token",
    }
    removal_message = Message(type=MsgType.ACCEPT_REMOVAL, payload=removal_payload)
    # Make the async generator yield our message then stop
    mock_dependencies["bus"].get.side_effect = [removal_message, None]

    # Mock the agent's internal methods
    agent._handle_accepted_removals = AsyncMock()
    agent._detect_and_propose = AsyncMock() # We don't want to test this part now
    agent.last_detection_time = 0 # Ensure detection doesn't run

    # Act
    await agent.on_tick()

    # Assert
    # We assert that the main handler was called. The detailed logic within
    # _handle_accepted_removals is tested in integration tests.
    agent._handle_accepted_removals.assert_called_once()
