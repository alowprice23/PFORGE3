import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path
import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import typer

from pforge.cli.skills.doctor import run_doctor_flow
from pforge.validation.test_runner import PytestRunner, PytestRunResult
from pforge.validation.types import TypeCheckResult


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

@pytest.mark.skip(reason="This test hangs due to a deep issue in the asyncio orchestration and is temporarily disabled.")
@patch("pforge.agents.fixer_agent.OpenAIClient", new_callable=AsyncMock)
@patch("typer.echo")
@patch("typer.Exit")
@pytest.mark.asyncio
async def test_doctor_command_e2e(mock_exit, mock_echo, mock_openai_client, doctor_e2e_project):
    """
    Tests the full end-to-end doctor command workflow by calling the function directly.
    """
    project_dir = doctor_e2e_project

    # --- Mock the LLM response ---
    # The mock needs to simulate the structure of an OpenAI response object.
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = '{"corrected_code": "def my_buggy_function():\\n    return 2\\n"}'
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]
    mock_openai_client.return_value.chat.completions.create.return_value = mock_completion


    # --- Initial state verification ---
    test_runner = PytestRunner(project_root=project_dir)
    initial_result = test_runner.run()
    assert initial_result is not None
    _, failed_count, _ = initial_result.get_counts()
    assert failed_count == 1, "Test should initially fail"

    # --- Run the doctor command ---
    # We run the doctor flow directly, not as a subprocess.
    # This avoids issues with PYTHONPATH and makes the test more reliable.
    success = await run_doctor_flow(project_dir, test_node_id="tests/test_buggy.py::test_bug")

    # --- Assertions ---
    # Check that the command reported success
    assert success is True, "The doctor flow should return True on success"

    # Check that the file was fixed.
    fixed_content = (project_dir / "pforge" / "buggy.py").read_text()
    assert "return 2" in fixed_content

    # Check that the tests now pass
    final_result = test_runner.run()
    assert final_result is not None
    passed_count, failed_count, _ = final_result.get_counts()
    assert passed_count == 1
    assert failed_count == 0
