import asyncio
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import fakeredis.aioredis
import typer

from pforge.cli.skills.doctor import run_doctor_flow
from pforge.validation.test_runner import PytestRunner


class FakeOpenAIClient:
    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, *args, **kwargs):
        correct_code = "def my_buggy_function():\n    return 2"
        return f"```python\n{correct_code}\n```"

class MockTestRunResult:
    def __init__(self, passed, stdout, stderr, report_path=None):
        self.passed = passed
        self.stdout = stdout
        self.stderr = stderr
        self.report_path = report_path

    def to_dict(self):
        return { "passed": self.passed, "stdout": self.stdout, "stderr": self.stderr }


@pytest.fixture
def doctor_e2e_project():
    """Creates a temporary project with a single bug and a failing test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        (project_dir / "pforge.yaml").write_text(
            "doctor:\n  retry_limit: 1\n"
            "budget:\n  tenant: test-tenant\n  daily_quota_tokens: 1000\n"
            "planner:\n  effort_budget_per_tick: 30.0\n"
        )
        (project_dir / "buggy.py").write_text("def my_buggy_function():\n    return 1\n")
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").touch()
        (tests_dir / "test_buggy.py").write_text(
            "from buggy import my_buggy_function\n\n"
            "def test_bug():\n"
            "    assert my_buggy_function() == 2\n"
        )
        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True, capture_output=True)
        yield project_dir


@patch("pforge.agents.fixer_agent.PytestRunner")
@patch("redis.asyncio.from_url", return_value=fakeredis.aioredis.FakeRedis())
@patch("pforge.agents.fixer_agent.OpenAIClient", new=FakeOpenAIClient)
@pytest.mark.asyncio
async def test_doctor_command_e2e(mock_redis, mock_pytest_runner_class, doctor_e2e_project):
    """
    Tests the full end-to-end doctor command workflow.
    """
    project_dir = doctor_e2e_project

    # Configure the mock for PytestRunner used by the FixerAgent
    mock_runner_instance = mock_pytest_runner_class.return_value
    mock_runner_instance.run.return_value = MockTestRunResult(passed=True, stdout="fixed", stderr="")


    # --- Initial state verification ---
    # We call the real test_runner here for the initial check
    real_test_runner = PytestRunner(project_root=project_dir)
    initial_result = real_test_runner.run()
    assert not initial_result.passed, "Test should initially fail"

    # --- Run the doctor command ---
    await run_doctor_flow(project_dir, "tests/test_buggy.py::test_bug")

    # --- Final state verification ---
    final_content = (project_dir / "buggy.py").read_text()
    correct_code = "def my_buggy_function():\n    return 2"
    assert final_content.strip() == correct_code.strip()

    # The test runner inside the agent was mocked.
    # mock_pytest_runner_class.assert_called_once_with(project_root=project_dir)
    # mock_runner_instance.run.assert_called_once()

    # We can also run the real test runner again to make sure the file is truly fixed.
    final_result = real_test_runner.run()
    assert final_result.passed, "Test should pass after fix"
