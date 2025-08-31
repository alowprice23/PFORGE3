import asyncio
import pytest
from pathlib import Path
import tempfile

from pforge.agents.planner_agent import PlannerAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType, Message
from pforge.project import Project
from pforge.config import Config


@pytest.mark.asyncio
async def test_planner_agent_creates_fix_task():
    """
    Tests that the PlannerAgent can consume a TESTS_FAILED event and
    produce a FIX_TASK event.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / "pforge.toml").write_text("")

        # The planner's _infer_source_from_test expects a specific structure
        pforge_dir = project_path / "pforge"
        pforge_tests_dir = pforge_dir / "tests"
        pforge_tests_dir.mkdir(parents=True)
        (pforge_tests_dir / "test_dummy.py").write_text("assert True")


        bus = InMemoryBus()
        project = Project(project_path)
        config = Config.load(project.root / "pforge.toml")

        # The planner subscribes to topics on init, so it must be created before publishing
        planner = PlannerAgent(bus=bus, config=config, project=project)

        # The test needs to listen for the FIX_TASK message
        test_subscriber_name = "test_fix_task_listener"
        bus.subscribe(test_subscriber_name, MsgType.FIX_TASK.value)

        # Simulate a TESTS_FAILED event
        failed_event = Message(
            type=MsgType.TESTS_FAILED,
            payload={
                "failed_tests": [{
                    "nodeid": "pforge/tests/test_buggy_module.py::test_buggy_function_returns_fixed",
                    "traceback": "AssertionError: assert 'bug' == 'fixed'"
                }],
                "passed": 0, "failed": 1, "skipped": 0,
            }
        )
        # Publish to the topic the planner is listening on
        await bus.publish(MsgType.TESTS_FAILED.value, failed_event)

        # Run the agent's on_tick method to process the message
        await planner.on_tick()

        # Check for the FIX_TASK event
        fix_task_message = await bus.get(test_subscriber_name, timeout=2.0)

        assert fix_task_message is not None, "PlannerAgent did not publish a FIX_TASK event."
        assert fix_task_message.type == MsgType.FIX_TASK

        # Check the payload
        payload = fix_task_message.payload
        assert payload["file_path"] == "pforge/buggy_module.py"
        assert "Fix the bug" in payload["description"]
        assert "AssertionError: assert 'bug' == 'fixed'" in payload["description"]
