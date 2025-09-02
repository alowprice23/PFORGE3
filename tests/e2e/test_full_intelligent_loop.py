import asyncio
import orjson
import pytest
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

from pforge.config import Config
from pforge.project import Project
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import MsgType, Message
from pforge.validation.test_runner import run_tests

@pytest.fixture
def intelligent_loop_project(tmp_path):
    """
    Creates a temporary project with a bug that is tricky to fix,
    requiring more than one attempt.
    """
    project_dir = Path(tmp_path)
    (project_dir / "pforge.toml").write_text("[doctor]\nretry_limit = 1\n")

    source_dir = project_dir / "pforge"
    source_dir.mkdir()
    # The bug: The function should handle negative numbers correctly,
    # but a naive fix might just change `x > 0` to `x != 0`,
    # which is still wrong for negative inputs. A second attempt
    # should get it right.
    (source_dir / "buggy.py").write_text(
        "def check_number(x):\n"
        "    if x > 0:\n"
        "        return 'positive'\n"
        "    return 'zero or negative'\n"
    )

    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_buggy.py").write_text(
        "from pforge.buggy import check_number\n\n"
        "def test_positive():\n"
        "    assert check_number(5) == 'positive'\n\n"
        "def test_zero():\n"
        "    assert check_number(0) == 'zero'\n\n"
        "def test_negative():\n"
        "    assert check_number(-5) == 'negative'\n"
    )

    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True, capture_output=True)

    return project_dir

@pytest.mark.asyncio
async def test_full_intelligent_retry_loop(intelligent_loop_project):
    """
    Tests the full intelligent workflow:
    - Attempt 1 fails, is analyzed, and reverted.
    - Attempt 2 uses the analysis to succeed.
    """
    project_dir = intelligent_loop_project
    project = Project(project_dir)
    config = Config.load(path=project_dir / "pforge.toml")

    # --- Initial state verification ---
    initial_result = run_tests(test_nodes=[], source_root=project_dir)
    assert initial_result is not None
    # The initial code fails for 'zero' and 'negative'
    assert initial_result.failed == 2, "Two tests should initially fail"

    # --- Setup Orchestrator ---
    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    # --- Mock LLM Clients for the Scenario ---
    # 1. FixerAgent's LLM
    fixer_agent = next(a for a in orchestrator.agents if a.name == "fixer")
    mock_fixer_llm = AsyncMock()
    # Attempt 1: A naive but incorrect fix.
    # Attempt 2: The correct fix, prompted by the MisfitAgent's analysis.
    mock_fixer_llm.chat.side_effect = [
        (
            "def check_number(x):\n"
            "    if x > 0:\n"
            "        return 'positive'\n"
            "    elif x == 0:\n"
            "        return 'zero'\n"
            "    return 'zero or negative'\n" # Still wrong for negative
        ),
        (
            "def check_number(x):\n"
            "    if x > 0:\n"
            "        return 'positive'\n"
            "    elif x == 0:\n"
            "        return 'zero'\n"
            "    else:\n"
            "        return 'negative'\n"
        ),
    ]
    fixer_agent.llm_client = mock_fixer_llm

    # 2. PredictorAgent's LLM
    predictor_agent = next(a for a in orchestrator.agents if a.name == "predictor")
    mock_predictor_llm = AsyncMock()
    # Let it be confident in both patches for this test
    mock_predictor_llm.chat.return_value = orjson.dumps({"confidence": 0.9})
    predictor_agent.llm_client = mock_predictor_llm

    # 3. MisfitAgent's LLM
    misfit_agent = next(a for a in orchestrator.agents if a.name == "misfit")
    mock_misfit_llm = AsyncMock()
    mock_misfit_llm.chat.return_value = "The logic for negative numbers is still incorrect."
    misfit_agent.llm_client = mock_misfit_llm

    # --- Spy on the Planner ---
    planner = next(a for a in orchestrator.agents if a.name == "planner")
    with patch.object(planner, 'publish', wraps=planner.publish) as mock_planner_publish:
        # --- Run Orchestrator ---
        orchestrator_task = asyncio.create_task(orchestrator.run())

        # --- Kick off the process ---
        # The ObserverAgent will detect the initial failures and kick things off.
        # We'll just wait for the system to settle.
        await asyncio.sleep(25) # Give plenty of time for the full loop

        # --- Assertions ---
        # 1. Final state of the code should be correct
        final_code = (project_dir / "pforge" / "buggy.py").read_text()
        assert "else:\n        return 'negative'" in final_code

        # 2. Final tests should all pass
        final_result = run_tests(test_nodes=[], source_root=project_dir)
        assert final_result is not None
        assert final_result.passed == 3, "All three tests should pass in the end"
        assert final_result.failed == 0

        # 3. Check the planner's retry prompt included the misfit analysis
        fix_task_calls = [
            call for call in mock_planner_publish.call_args_list
            if call.args[0] == MsgType.FIX_TASK.value
        ]
        assert len(fix_task_calls) == 2, "Should have been 1 initial task and 1 retry"
        retry_description = fix_task_calls[1].args[1].payload["description"]
        assert "An AI assistant has analyzed the failure" in retry_description
        assert "The logic for negative numbers is still incorrect." in retry_description

        # --- Cleanup ---
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass
