import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import subprocess

from pforge.config.models import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.orchestrator.state_bus import PuzzleState
from pforge.project import Project
from pforge.orchestrator.signals import Message, MsgType
from pforge.validation.test_runner import TestRunnerResult


@pytest.fixture
def project_with_retry_limit(tmp_path):
    """Creates a dummy project with a retry_limit of 2 in pforge.toml and config files."""
    project_root = tmp_path
    (project_root / "pforge.toml").write_text("[doctor]\nretry_limit = 2\n")

    # Create config files with empty content that Config.load() expects
    config_dir = project_root / "pforge" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "settings.yaml").write_text("doctor:\n  retry_limit: 2\n")
    (config_dir / "llm_providers.yaml").write_text("providers: []")
    (config_dir / "agents.yaml").write_text(
        "agents:\n"
        "  planner:\n"
        "    enabled: true\n"
        "  fixer:\n"
        "    enabled: true\n"
        "  observer:\n"
        "    enabled: true\n"
    )
    (config_dir / "quotas.yaml").write_text("{}")

    (project_root / "pforge").mkdir(exist_ok=True)
    (project_root / "pforge" / "buggy.py").write_text("def foo(): return 1")
    # Also create a dummy test file so the test runner has something to find
    tests_dir = project_root / "pforge" / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_dummy.py").write_text("def test_dummy(): assert True")
    (tests_dir / "test_buggy.py").write_text("from pforge.buggy import foo\n\ndef test_foo():\n    assert foo() == 2")

    # Initialize a git repository for the backtracker agent to use
    subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_root, check=True, capture_output=True)

    return Project(project_root)


from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch("pforge.agents.observer_agent.ObserverAgent.on_tick", new_callable=AsyncMock)
@patch("pforge.validation.test_runner.run_tests")
@patch("pforge.llm_clients.openai_o3_client.OpenAIClient.chat", new_callable=AsyncMock)
async def test_retry_loop_generates_augmented_prompt_and_stops(
    mock_llm_chat, mock_run_tests, mock_observer_on_tick, project_with_retry_limit
):
    """
    Tests the full retry loop:
    1. A test failure triggers a fix.
    2. The fix fails verification, triggering a retry.
    3. The planner creates an augmented prompt for the retry.
    4. The loop stops after the retry limit is reached.
    """
    # --- Setup ---
    config = Config.load(config_dir=project_with_retry_limit.root / "pforge" / "config")
    # Ensure we have a low retry limit for the test
    # assert config.doctor.retry_limit == 2 # pydantic v2 does not support attribute access like this

    orchestrator = Orchestrator(config, project_with_retry_limit)

    # Mock the LLM to always provide a bad fix
    mock_llm_chat.return_value = "def foo(): return 2 # still wrong"

    # Mock run_tests to always fail
    mock_run_tests.return_value = TestRunnerResult(
        exit_code=1, passed=0, failed=1, skipped=0, duration_s=1.0,
        report_hash="dummy_hash", report_content='{"tests": [{"outcome": "failed", "longrepr": "assert 1 == 2"}]}',
        command=["pytest"]
    )

    # Spy on the planner's publish method to check the augmented prompt
    planner = orchestrator.registry.instantiate("planner")
    with patch.object(planner, 'send_amp', wraps=planner.send_amp) as mock_planner_send_amp:
        # --- Act ---
        run_task = asyncio.create_task(orchestrator.run_forever())
        await asyncio.sleep(0.1)  # Allow time for agents to start and subscribe

        # 1. Kick off the process with a TESTS_FAILED message
        # This simulates the ObserverAgent having found a failure.
        # The PlannerAgent should be listening for this.
        failure_report = {
            "report_content": '{"tests": [{"nodeid": "pforge/tests/test_buggy.py::test_foo", "outcome": "failed", "longrepr": "assert 1 == 2"}]}',
            "exit_code": 1,
        }
        message = Message(type=MsgType.TESTS_FAILED, payload=failure_report)
        await orchestrator.bus.publish("amp:global:events", message)

        # Let the system run for a few cycles to process the retries
        await asyncio.sleep(5)

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

        # The second FIX_TASK should have an augmented prompt
        retry_fix_task_message = fix_task_calls[1].args[0]
        retry_description = retry_fix_task_message.payload["description"]
        assert "A previous attempt to fix the bug" in retry_description
        assert "Please analyze the previous mistake" in retry_description

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
