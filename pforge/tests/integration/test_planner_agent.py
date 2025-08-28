import asyncio
import json
import pytest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock

from pforge.agents.planner_agent import PlannerAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType, Message
from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.project import Project
from pforge.config.models import Config


@pytest.mark.asyncio
async def test_planner_agent_creates_fix_task():
    """
    Tests that the PlannerAgent can consume a TESTS_FAILED event and
    produce a FIX_TASK event.
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

        # The planner's _infer_source_from_test expects a specific structure
        pforge_dir = project_path / "pforge"
        pforge_tests_dir = pforge_dir / "tests"
        pforge_tests_dir.mkdir(parents=True)
        (pforge_tests_dir / "test_dummy.py").write_text("assert True")


        bus = InMemoryBus()
        project = Project(project_path)
        mock_state_bus = MagicMock(spec=StateBus)
        mock_eff_engine = MagicMock(spec=EfficiencyEngine)


        # The planner subscribes to topics on init, so it must be created before publishing
        planner = PlannerAgent(
            bus=bus,
            state_bus=mock_state_bus,
            eff_engine=mock_eff_engine,
            project=project
        )
        await planner.on_startup() # This is the crucial step

        # The test needs to listen for the FIX_TASK message
        test_subscriber_name = "test_fix_task_listener"
        bus.subscribe(test_subscriber_name, MsgType.FIX_PATCH_PROPOSED.value)

        # Simulate a TESTS_FAILED event
        report_content = json.dumps({
            "tests": [{
                "nodeid": "pforge/tests/test_buggy_module.py::test_buggy_function_returns_fixed",
                "outcome": "failed",
                "longrepr": "AssertionError: assert 'bug' == 'fixed'"
            }]
        })
        failed_event = Message(
            type=MsgType.TESTS_FAILED,
            payload={
                "report_content": report_content,
                "exit_code": 1,
            }
        )
        # Publish to the topic the planner is listening on
        await bus.publish("amp:global:events", failed_event)

        # Run the agent's on_tick method to process the message
        await planner.on_tick(PuzzleState())

        # Check for the FIX_TASK event
        fix_task_messages = await bus.get(test_subscriber_name, timeout=2.0)
        assert fix_task_messages, "PlannerAgent did not publish a FIX_TASK event."
        fix_task_message = fix_task_messages[0]
        assert fix_task_message.type == MsgType.FIX_PATCH_PROPOSED

        # Check the payload
        payload = fix_task_message.payload
        assert payload["file_path"] == "pforge/buggy_module.py"
        assert "Fix the bug" in payload["description"]
        assert "AssertionError: assert 'bug' == 'fixed'" in payload["description"]
