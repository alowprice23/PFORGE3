import tempfile
from pathlib import Path

import pytest

from pforge.agents.observer_agent import ObserverAgent
from pforge.config import Config
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType
from pforge.project import Project
from pforge.validation.test_runner import PytestRunner
from pforge.validation.dep_graph import DependencyGraph
from pforge.validation.coverage_index import CoverageIndex
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_observer_agent_detects_failure():
    """
    Tests that the ObserverAgent can run tests and publish a TESTS_FAILED event.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        # The agent needs a pforge.yaml to initialize Config
        (project_path / "pforge.yaml").write_text("doctor:\n  retry_limit: 1\n")

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
        config = Config.load(project.root / "pforge.yaml")

        test_runner = PytestRunner(project_root=project.root)
        dep_graph = DependencyGraph(project_root=project.root)
        coverage_index = CoverageIndex(project_root=project.root)
        coverage_index.load()

        observer = ObserverAgent(
            bus=bus,
            config=config,
            project=project,
            test_runner=test_runner,
            dep_graph=dep_graph,
            coverage_index=coverage_index,
        )

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
