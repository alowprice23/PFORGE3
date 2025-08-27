import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from pforge.config import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project
from pforge.validation.test_runner import TestRunnerResult


@pytest.fixture
def project_with_retry_limit(tmp_path):
    """Creates a dummy project with a retry_limit of 2 in pforge.toml."""
    (tmp_path / "pforge").mkdir()
    (tmp_path / "pforge.toml").write_text("[doctor]\nretry_limit = 2\n")
    project_root = tmp_path
    (project_root / "src").mkdir()
    (project_root / "src" / "buggy.py").write_text("def foo(): return 1")
    return Project(project_root)


@pytest.mark.asyncio
@patch("pforge.agents.fixer_agent.run_tests")
@patch("pforge.agents.fixer_agent.OpenAIClient")
async def test_retry_loop_generates_augmented_prompt_and_stops(
    mock_openai_client_constructor, mock_run_tests, project_with_retry_limit
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
    mock_llm_instance = MagicMock()
    mock_llm_instance.chat = AsyncMock(return_value="def foo(): return 2 # still wrong")
    mock_openai_client_constructor.return_value = mock_llm_instance

    # Mock run_tests to always fail
    mock_run_tests.return_value = TestRunnerResult(
        exit_code=1, passed=0, failed=1, skipped=0, duration_s=1.0,
        report_hash="dummy_hash", report_content='{"tests": [{"outcome": "failed", "longrepr": "assert 1 == 2"}]}',
        command=["pytest"]
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

        # Let the system run for a few cycles to process the retries
        await asyncio.sleep(5)

        # --- Assert ---
        # The FixerAgent should have been called 3 times:
        # 1 initial attempt + 2 retries (since retry_limit is 2)
        assert mock_llm_instance.chat.call_count == 3

        # The planner should have published 3 FIX_TASKs
        # 1 initial, 2 for retries
        fix_task_calls = [
            call for call in mock_planner_publish.call_args_list
            if call.args[0] == MsgType.FIX_TASK.value
        ]
        assert len(fix_task_calls) == 3

        # The second FIX_TASK should have an augmented prompt
        retry_fix_task_message = fix_task_calls[1].args[1]
        retry_description = retry_fix_task_message.payload["description"]
        assert "A previous attempt to fix the bug" in retry_description
        assert "Please analyze the previous mistake" in retry_description

        # The orchestrator should have logged that it's giving up
        # We can't easily check logs here, but the call count implies it stopped.

        # --- Cleanup ---
        run_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await run_task
