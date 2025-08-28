import asyncio
import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, AsyncMock
import orjson
import subprocess

from pforge.config.models import Config
from pforge.project import Project
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import MsgType, Message
from pforge.validation.test_runner import run_tests

@pytest.fixture
def e2e_project():
    """Creates a temporary project with a single bug and a failing test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create a valid, isolated config for the test
        config_dir = project_dir / "pforge" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "settings.yaml").write_text("doctor:\n  retry_limit: 1\n")
        (config_dir / "llm_providers.yaml").write_text("providers: []\n")
        (config_dir / "quotas.yaml").write_text("quotas: []\n")
        (config_dir / "agents.yaml").write_text(
            "agents:\n"
            "  observer:\n"
            "    enabled: true\n"
            "  planner:\n"
            "    enabled: true\n"
            "  fixer:\n"
            "    enabled: true\n"
        )


        source_dir = project_dir / "pforge"
        source_dir.mkdir(exist_ok=True)
        (source_dir / "__init__.py").touch()
        (source_dir / "buggy.py").write_text("def my_buggy_function():\n    return 1\n")

        tests_dir = project_dir / "pforge" / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").touch()
        (tests_dir / "test_buggy.py").write_text(
            "from pforge.buggy import my_buggy_function\n\n"
            "def test_bug():\n"
            "    assert my_buggy_function() == 2\n"
        )

        # Initialize git for the BacktrackerAgent
        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True, capture_output=True)

        yield project_dir

@pytest.mark.asyncio
@patch("pforge.llm_clients.openai_o3_client.OpenAIClient.chat", new_callable=AsyncMock)
async def test_e2e_full_loop(mock_llm_chat, e2e_project):
    """
    Tests the full end-to-end loop:
    1. Observer detects a failure.
    2. Planner creates a fix task.
    3. Fixer (mocked) provides a correct patch.
    4. Observer verifies the fix and confirms tests pass.
    """
    project_dir = e2e_project
    project = Project(project_dir)
    config = Config.load(project_dir / "pforge" / "config")

    # --- Mock the LLM response ---
    correct_code = "def my_buggy_function():\n    return 2\n"
    mock_llm_chat.return_value = correct_code

    # --- Initial state verification ---
    # Use the robust run_tests function we've already fixed
    initial_result = run_tests(test_nodes=[], source_root=project_dir)
    assert initial_result is not None
    assert initial_result.failed == 1, "Test should initially fail"

    # --- Setup Orchestrator and listener ---
    orchestrator = Orchestrator(config, project)

    # We will listen for the final QED_EMITTED signal
    bus = orchestrator.bus
    test_subscriber = "e2e_test_listener"
    bus.subscribe(test_subscriber, MsgType.QED_EMITTED.value)

    # --- Run the Orchestrator ---
    orchestrator_task = asyncio.create_task(orchestrator.run_forever())
    await asyncio.sleep(0.1) # Allow time for agents to start and subscribe

    # Manually kick off the process by sending the first TESTS_FAILED message
    # This is faster and more reliable for a test than waiting for the Observer's tick
    # Parse the report to create a realistic payload, mirroring the ObserverAgent's logic
    report_data = orjson.loads(initial_result.report_content)
    failed_tests_processed = []
    for test in report_data.get("tests", []):
        if test.get("outcome") == "failed":
            failed_tests_processed.append({
                "nodeid": test.get("nodeid"),
                "traceback": test.get("longrepr", "")
            })
    initial_failed_message = Message(
        type=MsgType.TESTS_FAILED,
        payload={
                "report_content": initial_result.report_content,
                "exit_code": initial_result.exit_code,
        }
    )
    await bus.publish("amp:global:events", initial_failed_message)

    # --- Wait for the outcome ---
    try:
        # Wait for the QED_EMITTED message that signals a successful fix
        final_messages = await bus.get(test_subscriber, timeout=20.0)
        assert final_messages, "Did not receive any message on the bus"
        final_message = final_messages[0]
        assert final_message.type == MsgType.QED_EMITTED
    except asyncio.TimeoutError:
        pytest.fail("Test timed out waiting for a fix to be applied and verified.")
    finally:
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass  # This is expected if the task was still running

    # --- Final state verification ---
    # Verify that the tests now pass
    final_result = run_tests(test_nodes=[], source_root=project_dir)
    assert final_result is not None
    assert final_result.passed == 1, "Tests should pass after the fix"
    assert final_result.failed == 0
