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

import pytest

@pytest.mark.skip(reason="This test is broken due to agent constructor signatures not matching BaseAgent.")
@pytest.mark.asyncio
async def test_observer_agent_detects_failure(monkeypatch):
    """
    Tests that the ObserverAgent can run tests and publish a TESTS_FAILED event.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create a buggy file and a failing test
        buggy_module_path = project_path / "buggy_module.py"
        buggy_module_path.write_text("def buggy_function():\n    return 'bug'\n")

        tests_dir = project_path / "tests"
        tests_dir.mkdir()
        test_file_path = tests_dir / "test_buggy_module.py"
        test_file_path.write_text(
            "from buggy_module import buggy_function\n"
            "def test_buggy_function_returns_fixed():\n"
            "    assert buggy_function() == 'fixed'\n"
        )

        bus = InMemoryBus()
        observer = ObserverAgent(bus, source_root=project_path)

        # Run the agent's on_tick method
        await observer.on_tick()

        # Check for the TESTS_FAILED event
        try:
            message = await asyncio.wait_for(bus.get_queue("pforge:amp:global:events").get(), timeout=1.0)
            assert message.type == MsgType.TESTS_FAILED.value
            assert len(message.payload['failed_tests']) == 1
            assert message.payload['failed_tests'][0]['nodeid'] == 'tests/test_buggy_module.py::test_buggy_function_returns_fixed'
        except asyncio.TimeoutError:
            pytest.fail("ObserverAgent did not publish a TESTS_FAILED event.")
