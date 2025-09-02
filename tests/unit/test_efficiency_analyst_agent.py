import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from pforge.agents.efficiency_analyst_agent import EfficiencyAnalystAgent
from pforge.orchestrator.signals import Message, MsgType, GapDelta
from pforge.orchestrator.state_bus import PuzzleState

@pytest.fixture
def mock_bus():
    bus = MagicMock()
    bus.get = AsyncMock()
    bus.publish = AsyncMock()
    return bus

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get.return_value = {} # for spec_config
    return config

@pytest.fixture
def test_agent(mock_bus, mock_config):
    project = MagicMock()
    agent = EfficiencyAnalystAgent(bus=mock_bus, config=mock_config, project=project)
    # Mock the dependencies that are created inside the agent
    agent.state_bus = MagicMock()
    agent.state_bus.get_snapshot.return_value = PuzzleState(gaps=5)
    agent.state_bus.publish_update = AsyncMock() # This needs to be awaitable
    agent.efficiency_engine = MagicMock()
    agent.efficiency_engine.compute.return_value = 0.99
    return agent

@pytest.mark.asyncio
async def test_efficiency_analyst_applies_delta(test_agent, mock_bus):
    # Prepare a delta message to be in the queue
    delta_message = Message(type=MsgType.GAP_DELTA, payload={"agent_name": "fixer", "value": -1})
    mock_bus.get.side_effect = [delta_message, None] # Return one message, then None to stop the loop

    # Run the agent's main logic
    await test_agent.on_tick()

    # 1. Assert the agent got the current state
    test_agent.state_bus.get_snapshot.assert_called_once()

    # 2. Assert the state was updated correctly
    updated_state = test_agent.state_bus.get_snapshot.return_value
    assert updated_state.gaps == 4 # Initial state was 5, delta was -1

    # 3. Assert the efficiency engine was called with the updated state
    test_agent.efficiency_engine.compute.assert_called_once_with(updated_state)

    # 4. Assert the state bus was told to publish the update
    test_agent.state_bus.publish_update.assert_called_once_with(updated_state)

    # 5. Assert a METRICS_UPDATED message was published
    # The first call to publish() is the METRICS_UPDATED one.
    # The second is the one from the superclass publish method.
    assert mock_bus.publish.call_count > 0
    published_message = mock_bus.publish.call_args_list[0][0][1]
    assert published_message.type == MsgType.METRICS_UPDATED
    assert published_message.payload["tick"] == 1
