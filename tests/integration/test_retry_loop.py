import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import orjson

import pytest
import subprocess

from pforge.config import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project
from pforge.validation.test_runner import TestRunnerResult


@pytest.fixture
def project_with_retry_limit(tmp_path):
    """Creates a dummy project with a retry_limit of 2 in pforge.toml."""
    project_root = tmp_path
    (project_root / "pforge.toml").write_text("[doctor]\nretry_limit = 2\n")

    source_dir = project_root / "pforge"
    source_dir.mkdir()
    (source_dir / "buggy.py").write_text("def foo(): return 1")

    tests_dir = project_root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_dummy.py").write_text("def test_dummy(): assert True")
    (tests_dir / "test_buggy.py").write_text("from pforge.buggy import foo\n\ndef test_foo():\n    assert foo() == 2")

    # Initialize a git repository for the backtracker agent to use
    subprocess.run(["git", "init"], cwd=project_root, check=True)
    subprocess.run(["git", "add", "."], cwd=project_root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_root, check=True)

    return Project(project_root)


from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch("pforge.agents.observer.ObserverAgent.on_tick", new_callable=AsyncMock)
@patch("pforge.agents.fixer_agent.run_tests")
async def test_retry_loop_generates_augmented_prompt_and_stops(
    mock_run_tests, mock_observer_on_tick, project_with_retry_limit
):
    """
    Tests the full intelligent retry loop:
    1. A test failure triggers a fix.
    2. The fix is predicted to be okay.
    3. The fix fails verification tests, triggering a retry.
    4. The MisfitAgent analyzes the failure.
    5. The Planner creates an augmented prompt for the retry, including the analysis.
    6. The loop stops after the retry limit is reached.
    """
    # --- Setup ---
    config = Config.load(path=project_with_retry_limit.root / "pforge.toml")
    assert config.doctor.retry_limit == 2

    orchestrator = Orchestrator(config, project_with_retry_limit)
    orchestrator.setup_agents()

    # --- Mock Agent LLM Clients ---
    # Mock FixerAgent to always provide a bad fix
    fixer_agent = next(a for a in orchestrator.agents if a.name == "fixer")
    mock_fixer_llm = AsyncMock()
    mock_fixer_llm.chat.return_value = "def foo(): return 2 # still wrong"
    fixer_agent.llm_client = mock_fixer_llm

    # Mock PredictorAgent to always be confident
    predictor_agent = next(a for a in orchestrator.agents if a.name == "predictor")
    mock_predictor_llm = AsyncMock()
    mock_predictor_llm.chat.return_value = orjson.dumps({"confidence": 1.0})
    predictor_agent.llm_client = mock_predictor_llm

    # Mock MisfitAgent to provide a canned analysis
    misfit_agent = next(a for a in orchestrator.agents if a.name == "misfit")
    mock_misfit_llm = AsyncMock()
    mock_misfit_llm.chat.return_value = "AI analysis: The core logic is flawed."
    misfit_agent.llm_client = mock_misfit_llm

    # --- Mock Test Runner ---
    # Mock run_tests to always fail
    mock_run_tests.return_value = TestRunnerResult(
        exit_code=1, passed=0, failed=1, skipped=0, duration_s=1.0,
        report_hash="dummy_hash", report_content='{"tests": [{"outcome": "failed", "longrepr": "assert 1 == 2"}]}',
        command=["pytest"]
    )

    # --- Spy on Planner ---
    planner = next(a for a in orchestrator.agents if a.name == "planner")
    with patch.object(planner, 'publish', wraps=planner.publish) as mock_planner_publish:
        # --- Act ---
        run_task = asyncio.create_task(orchestrator.run())

        # Kick off the process with a TESTS_FAILED message
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
        # The FixerAgent's LLM should have been called 3 times (1 initial + 2 retries)
        assert mock_fixer_llm.chat.call_count == 3

        # The planner should have published 3 FIX_TASKs
        fix_task_calls = [
            call for call in mock_planner_publish.call_args_list
            if call.args[0] == MsgType.FIX_TASK.value
        ]
        assert len(fix_task_calls) == 3

        # The second FIX_TASK should have the fully augmented prompt
        retry_fix_task_message = fix_task_calls[1].args[1]
        retry_description = retry_fix_task_message.payload["description"]
        assert "A previous attempt to fix the bug" in retry_description
        assert "assert 1 == 2" in retry_description
        assert "AI analysis: The core logic is flawed." in retry_description

        # --- Cleanup ---
        # The orchestrator should stop on its own after giving up.
        # We cancel here to be sure the task is cleaned up, but it might already be done.
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            # This is expected if the task was still running.
            pass
