import asyncio
import os
import tempfile
import pytest
from pathlib import Path

from pforge.agents.observer_agent import ObserverAgent
from pforge.orchestrator.state_bus import StateBus
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType

from pforge.project import Project
from pforge.config import Config


@pytest.mark.asyncio
async def test_observer_agent_detects_failure():
    """
    Tests that the ObserverAgent can run tests and publish a TESTS_FAILED event.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create a valid, isolated config for the test
        config_dir = project_path / "pforge" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "settings.yaml").write_text("doctor:\n  retry_limit: 1\n")
        (config_dir / "llm_providers.yaml").write_text("providers: []\n")
        (config_dir / "quotas.yaml").write_text("quotas: []\n")
        (config_dir / "agents.yaml").write_text(
            "agents:\n"
            "  observer:\n"
            "    enabled: true\n"
        )

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
        config = Config.load(config_dir=config_dir)

        observer = ObserverAgent(bus=bus, config=config, project=project)

        # Subscribe to the event stream to listen for the result
        test_subscriber_name = "test_listener"
        bus.subscribe(test_subscriber_name, MsgType.TESTS_FAILED.value)

        # Run the agent's on_tick method
        await observer.on_tick()

        # Check for the TESTS_FAILED event
        message = await bus.get(test_subscriber_name, timeout=2.0)

        assert message is not None, "ObserverAgent did not publish a TESTS_FAILED event."
        assert message.type == MsgType.TESTS_FAILED
        assert len(message.payload['failed_tests']) == 1
        assert message.payload['failed_tests'][0]['nodeid'] == 'tests/test_buggy_module.py::test_buggy_function_returns_fixed'
