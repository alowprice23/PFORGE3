import asyncio
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from pforge.agents.observer_agent import ObserverAgent
from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType

from pforge.project import Project
from pforge.config.models import Config


@pytest.mark.asyncio
async def test_observer_agent_detects_failure():
    """
    Tests that the ObserverAgent can run tests and publish a TESTS_FAILED event.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create a dummy config file
        config_dir = project_path / "pforge" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "settings.yaml").write_text("doctor:\n  retry_limit: 2\n")
        (config_dir / "llm_providers.yaml").write_text("providers: []\n")
        (config_dir / "agents.yaml").write_text("agents: []\n")
        (config_dir / "quotas.yaml").write_text("quotas: []\n")

        # Create a buggy file and a failing test
        (project_path / "buggy_module.py").write_text("def buggy_function():\n    return 'bug'\n")

        tests_dir = project_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_buggy_module.py").write_text(
            "from buggy_module import buggy_function\n"
            "def test_buggy_function_returns_fixed():\n"
            "    assert buggy_function() == 'fixed'\n"
        )

        bus = InMemoryBus()
        project = Project(project_path)
        # These dependencies are now passed directly to the agent
        mock_state_bus = MagicMock(spec=StateBus)
        mock_eff_engine = MagicMock(spec=EfficiencyEngine)

        observer = ObserverAgent(
            bus=bus,
            state_bus=mock_state_bus,
            eff_engine=mock_eff_engine,
            project=project
        )
        await observer.on_startup()

        # Subscribe to the event stream to listen for the result
        test_subscriber_name = "test_listener"
        bus.subscribe(test_subscriber_name, MsgType.TESTS_FAILED.value)

        # Run the agent's on_tick method
        await observer.on_tick(PuzzleState())

        # Check for the TESTS_FAILED event
        messages = await bus.get(test_subscriber_name, timeout=2.0)
        assert messages, "ObserverAgent did not publish a TESTS_FAILED event."
        message = messages[0]
        assert message.type == MsgType.TESTS_FAILED
        assert "report_content" in message.payload
        assert isinstance(message.payload["report_content"], str)
        assert "test_buggy_function_returns_fixed" in message.payload["report_content"]
