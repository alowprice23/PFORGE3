import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pforge.validation.test_runner import run_tests


@pytest.fixture
def doctor_e2e_project():
    """Creates a temporary project with a single bug and a failing test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        (project_dir / "pforge.toml").write_text("[doctor]\nretry_limit = 1\n")

        source_dir = project_dir / "pforge"
        source_dir.mkdir()
        (source_dir / "__init__.py").touch()
        (source_dir / "buggy.py").write_text("def my_buggy_function():\n    return 1\n")

        tests_dir = project_dir / "tests"
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

@patch("pforge.llm_clients.openai_o3_client.OpenAIClient.chat", new_callable=AsyncMock)
def test_doctor_command_e2e(mock_llm_chat, doctor_e2e_project):
    """
    Tests the full end-to-end doctor command workflow.
    """
    project_dir = doctor_e2e_project

    # --- Mock the LLM response ---
    correct_code = "```python\ndef my_buggy_function():\n    return 2\n```"
    mock_llm_chat.return_value = correct_code

    # --- Initial state verification ---
    initial_result = run_tests(test_nodes=[], source_root=project_dir)
    assert initial_result is not None
    assert initial_result.failed == 1, "Test should initially fail"

    # --- Run the doctor command ---
    command = [
        sys.executable,
        "-m",
        "pforge.cli.main",
        "doctor",
        "run",
        ".",
        "--test-node-id",
        "tests/test_buggy.py::test_bug",
    ]

    # We need to set the OPENAI_API_KEY for the FixerAgent to be created.
    env = {"OPENAI_API_KEY": "dummy"}

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
    )

    print("--- stdout ---")
    print(result.stdout)
    print("--- stderr ---")
    print(result.stderr)

    assert result.returncode == 0, "The doctor command should exit with a success code."
    assert "✅ Doctor workflow complete: Puzzle solved!" in result.stdout

    # --- Final state verification ---
    final_result = run_tests(test_nodes=[], source_root=project_dir)
    assert final_result is not None
    assert final_result.passed == 1, "Tests should pass after the fix"
    assert final_result.failed == 0
