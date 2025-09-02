import pytest
from unittest.mock import MagicMock, AsyncMock

from pforge.project import Project
from pforge.agents.spec_oracle_agent import SpecOracleAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message, MsgType

@pytest.fixture
def temp_project_with_violation(tmp_path):
    """Creates a project with a file that violates a spec rule."""
    (tmp_path / "pforge").mkdir()
    (tmp_path / "pforge" / "server").mkdir()
    (tmp_path / "pforge" / "server" / "app.py").write_text("# Dummy server file")

    (tmp_path / "pforge" / "agents").mkdir()
    # This file has a disallowed import
    (tmp_path / "pforge" / "agents" / "some_agent.py").write_text("from pforge.server import app\n\n# Bad import")
    return Project(tmp_path)

@pytest.fixture
def mock_config_with_spec():
    config = MagicMock()

    # Replicate the nested structure of the real Config object
    spec_config = {
        "disallowed_imports": {
            "enabled": True,
            "rules": [
                {"from": "pforge.agents", "disallow": "pforge.server"}
            ]
        }
    }
    config.specifications.raw_config = spec_config
    return config

@pytest.mark.asyncio
async def test_spec_oracle_detects_violation(temp_project_with_violation, mock_config_with_spec):
    bus = InMemoryBus()

    # Initialize the agent with the special config
    agent = SpecOracleAgent(bus=bus, config=mock_config_with_spec, project=temp_project_with_violation)

    # The bus needs a subscriber for the outgoing message, we can use a mock for that
    mock_subscriber = AsyncMock()
    bus.subscribe("test_subscriber", MsgType.SPEC_CHECKED.value)

    # 1. Publish a message indicating the file was "patched"
    patch_applied_msg = Message(
        type=MsgType.FIX_PATCH_APPLIED,
        payload={"file_path": "pforge/agents/some_agent.py"}
    )
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, patch_applied_msg)

    # 2. Run the agent's tick to process the message
    await agent.on_tick()

    # 3. Check the bus for the result
    result_msg = await bus.get("test_subscriber", timeout=0.1)

    # 4. Assert the result shows a spec violation
    assert result_msg is not None
    assert result_msg.type == MsgType.SPEC_CHECKED
    payload = result_msg.payload
    assert payload["is_valid"] is False

    # 5. Assert the details of the check are correct
    assert len(payload["checks"]) == 1
    disallowed_check = payload["checks"][0]
    assert disallowed_check["check"] == "disallowed_imports"
    assert disallowed_check["passed"] is False
    assert "disallowed module" in disallowed_check["output"]
