import asyncio
import subprocess
from unittest.mock import AsyncMock, patch

import pytest

from pforge.config import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project
from pforge.validation.test_runner import PytestRunResult


@pytest.fixture
def project_with_retry_limit(tmp_path):
    """Creates a dummy project with a retry_limit of 2 in pforge.toml."""
    (tmp_path / "pforge").mkdir()
    (tmp_path / "pforge.toml").write_text("[doctor]\nretry_limit = 2\n")
    project_root = tmp_path
    (project_root / "pforge").mkdir(exist_ok=True)
    (project_root / "pforge" / "buggy.py").write_text("def foo(): return 1")
    # Also create a dummy test file so the test runner has something to find
    tests_dir = project_root / "pforge" / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_dummy.py").write_text("def test_dummy(): assert True")
    (tests_dir / "test_buggy.py").write_text("from pforge.buggy import foo\n\ndef test_foo():\n    assert foo() == 2")

    # Initialize a git repository for the backtracker agent to use
    subprocess.run(["git", "init"], cwd=project_root, check=True)
    subprocess.run(["git", "add", "."], cwd=project_root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_root, check=True)

    return Project(project_root)



@pytest.mark.asyncio
@patch("pforge.agents.observer_agent.ObserverAgent.on_tick", new_callable=AsyncMock)
@patch("pforge.agents.fixer_agent.PytestRunner.run")
@patch("pforge.llm_clients.openai_o3_client.OpenAIClient.chat", new_callable=AsyncMock)
async def test_retry_loop_generates_augmented_prompt_and_stops(
    mock_llm_chat, mock_pytest_run, mock_observer_on_tick, project_with_retry_limit
):
    """
    Tests the full retry loop:
    1. A test failure triggers a fix.
    2. The fix fails verification, triggering a retry.
    3. The planner creates an augmented prompt for the retry.
    4. The loop stops after the retry limit is reached.
    """
    # --- Setup ---
    config = Config.load(path=project_with_retry_limit.root / "pforge.toml")
    # Ensure we have a low retry limit for the test
    assert config.doctor.retry_limit == 2

    orchestrator = Orchestrator(config, project_with_retry_limit)
    orchestrator.setup_agents()

    # Mock the LLM to always provide a bad fix
    mock_llm_chat.return_value = "def foo(): return 2 # still wrong"

    # Mock run to always fail
    mock_pytest_run.return_value = PytestRunResult(
        exit_code=1,
        junit_xml_path=None, # Not needed for this test
        report_hash="dummy_hash",
        stdout="dummy stdout",
        stderr="dummy stderr",
    )

    # Spy on the planner's publish method to check the augmented prompt
    planner = next(a for a in orchestrator.agents if a.name == "planner")
    with patch.object(planner, 'publish', wraps=planner.publish) as mock_planner_publish:
        # --- Act ---
        run_task = asyncio.create_task(orchestrator.run())

        # 1. Kick off the process with a TESTS_FAILED message
        initial_test_failure_message = Message(
            type=MsgType.TESTS_FAILED,
            payload={
                "failed_tests": [{
                    "nodeid": "tests/test_buggy.py::test_foo",
                    "traceback": "Initial traceback: assert 1 == 2"
                }]
            }
        )
        await orchestrator.bus.publish(MsgType.TESTS_FAILED.value, initial_test_failure_message)

        # --- Wait for the outcome ---
        bus = orchestrator.bus
        test_subscriber = "e2e_test_listener"
        bus.subscribe(test_subscriber, MsgType.GIVE_UP.value)

        try:
            # Wait for the GIVE_UP message that signals the end of retries
            final_message = await bus.get(test_subscriber, timeout=20.0)
            assert final_message is not None
            assert final_message.type == MsgType.GIVE_UP
        except (TimeoutError, asyncio.TimeoutError):
            pytest.fail("Test timed out waiting for the GIVE_UP signal.")

        # --- Assert ---
        # The FixerAgent should have been called 3 times:
        # 1 initial attempt + 2 retries (since retry_limit is 2)
        assert mock_llm_chat.call_count == 3

        # The planner should have published 3 FIX_TASKs
        # 1 initial, 2 for retries
        fix_task_calls = [
            call for call in mock_planner_publish.call_args_list
            if call.args[0] == MsgType.FIX_TASK.value
        ]
        assert len(fix_task_calls) == 3

        # The second FIX_TASK should have `failed_fix_info` in its payload
        retry_fix_task_message = fix_task_calls[1].args[1]
        assert "failed_fix_info" in retry_fix_task_message.payload, \
            "The payload of a retry task should contain information about the previous failed fix."

        # The orchestrator should have logged that it's giving up
        # We can't easily check logs here, but the call count implies it stopped.

        # --- Cleanup ---
        # The orchestrator should stop on its own after giving up.
        # We cancel here to be sure the task is cleaned up, but it might already be done.
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            # This is expected if the task was still running.
            pass
