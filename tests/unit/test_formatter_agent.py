import asyncio
import uuid

import pytest

from pforge.agents import FormatterAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project
from pforge.proof.capabilities import issue_token


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary python file with unformatted code."""
    file_path = tmp_path / "test_file.py"
    file_path.write_text("import os\n\ndef my_func():\n  pass\n")
    return file_path

@pytest.mark.asyncio
async def test_formatter_agent(temp_file):
    """Tests the formatting capability of the FormatterAgent."""
    # Arrange
    bus = InMemoryBus()

    class MockConfig:
        def __init__(self):
            self.llm = {"model": "gpt-4-turbo"}
            self.doctor = {"retry_limit": 3}
            self.specifications = {"raw_config": {}}
            self.recovery = {"enabled": False, "checks": []}
            self.budget = {"tenant": "test-tenant", "daily_quota_tokens": 1000}
            self.planner = {"effort_budget_per_tick": 30.0}

    config = MockConfig()
    project = Project(root_path=temp_file.parent)
    agent = FormatterAgent(bus, config, project)

    # Subscribe to the result channel BEFORE the action
    bus.subscribe("test_listener", MsgType.FILE_FORMATTED.value)
    bus.subscribe("test_listener_failed", MsgType.FORMATTING_FAILED.value)

    # Act
    op_id = f"format_{uuid.uuid4()}"
    token = issue_token(agent.name, ["fs:read", "fs:write"], op_id)

    # Publish to the TOPIC the agent is subscribed to.
    payload = {
        "file_path": str(temp_file.name),
        "op_id": op_id,
        "capability_token": token,
    }
    await bus.publish(MsgType.FORMAT_FILE.value, Message(type=MsgType.FORMAT_FILE, payload=payload))
    await asyncio.sleep(0.01) # Let the event loop process the message
    await agent.on_tick()

    # Assert
    message = await bus.get("test_listener", timeout=2)

    if message is None:
        failure_message = await bus.get("test_listener_failed", timeout=1)
        assert failure_message is None, f"Formatting failed unexpectedly: {failure_message.payload.get('error') if failure_message else 'Unknown'}"

    assert message is not None, "Did not receive FILE_FORMATTED message."
    assert message.type == MsgType.FILE_FORMATTED
    assert message.payload["file_path"] == str(temp_file.name)

    formatted_code = temp_file.read_text()
    assert "import os\n\n\ndef my_func():\n    pass\n" in formatted_code
