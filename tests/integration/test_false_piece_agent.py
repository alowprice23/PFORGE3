from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pforge.agents.false_piece_agent import FalsePieceAgent
from pforge.agents.planner_agent import PlannerAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType
from pforge.project import Project


@pytest.fixture
def temp_project(tmp_path):
    """Creates a temporary project structure for testing."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("import utils\n\nprint('hello')")
    (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
    # This file is unreferenced
    (tmp_path / "src" / "unused.py").write_text("# I am not used by anyone")
    return Project(tmp_path)

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get.return_value = {} # for spec_config
    return config

@pytest.mark.asyncio
async def test_false_piece_propose_and_remove_flow(temp_project, mock_config):
    bus = InMemoryBus()

    # Mock the LLM client to always confirm the file is a false piece
    with patch('pforge.agents.false_piece_agent.OpenAIClient') as mock_llm:
        mock_llm.return_value.chat = AsyncMock(return_value='{"is_false_piece": true}')

        # Initialize the agents
        fp_agent = FalsePieceAgent(bus=bus, config=mock_config, project=temp_project)
        planner_agent = PlannerAgent(bus=bus, config=mock_config, project=temp_project)

        # 1. Run FalsePieceAgent to detect and propose
        fp_agent.detection_interval = 0 # ensure it runs now
        await fp_agent.on_tick()

        # 2. Run PlannerAgent, which will consume the proposals from the bus
        await planner_agent.on_tick()

        # 3. Find the ACCEPT_REMOVAL message for the correct file on the bus.
        # The planner may have dispatched multiple, so we loop.
        acceptance_msg = None
        while True:
            msg = await bus.get("false_piece", timeout=0.1)
            if not msg:
                break
            if msg.type == MsgType.ACCEPT_REMOVAL and msg.payload.get("file_path") == "src/unused.py":
                acceptance_msg = msg
                break
        assert acceptance_msg is not None
        assert acceptance_msg.type == MsgType.ACCEPT_REMOVAL
        assert "capability_token" in acceptance_msg.payload

        # Re-publish the message so the agent can process it.
        await bus.publish(MsgType.ACCEPT_REMOVAL.value, acceptance_msg)

        # 5. Run FalsePieceAgent again to execute the removal
        await fp_agent.on_tick()

        # 6. Assert the file was deleted
        assert not (temp_project.root / "src" / "unused.py").exists()
