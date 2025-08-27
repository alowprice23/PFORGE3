import asyncio
import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, AsyncMock
import orjson
import subprocess

from pforge.config import Config
from pforge.project import Project
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import MsgType, Message
from pforge.validation.test_runner import run_tests

@pytest.fixture
def e2e_project():
    """Creates a temporary project with a single bug and a failing test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        (project_dir / "pforge.toml").write_text("[doctor]\nretry_limit = 1\n")

        source_dir = project_dir / "pforge"
        source_dir.mkdir()
        (source_dir / "buggy.py").write_text("def my_buggy_function():\n    return 1\n")

        tests_dir = project_dir / "pforge" / "tests"
        tests_dir.mkdir()
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
    config = Config.load(path=project_dir / "pforge.toml")

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
    orchestrator.setup_agents()

    # We will listen for the final TESTS_PASSED signal
    bus = orchestrator.bus
    test_subscriber = "e2e_test_listener"
    bus.subscribe(test_subscriber, MsgType.TESTS_PASSED.value)

    # --- Run the Orchestrator ---
    orchestrator_task = asyncio.create_task(orchestrator.run())

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
            "failed_tests": failed_tests_processed,
            "failed": initial_result.failed,
            "passed": initial_result.passed,
        }
    )
    await bus.publish(MsgType.TESTS_FAILED.value, initial_failed_message)

    # --- Wait for the outcome ---
    try:
        # Wait for the TESTS_PASSED message that signals a successful fix
        final_message = await bus.get(test_subscriber, timeout=20.0)
        assert final_message is not None
        assert final_message.type == MsgType.TESTS_PASSED
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
