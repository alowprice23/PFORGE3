import pytest
import asyncio
from pathlib import Path
import subprocess
import toml
import typer
from unittest.mock import patch, AsyncMock

from pforge.cli.skills.doctor import run_doctor_flow

@pytest.fixture
def mock_config_dict():
    """Provides a default config as a dictionary."""
    return {
        "llm": {"model": "gpt-4-turbo"},
        "doctor": {"retry_limit": 3},
        "specifications": {"raw_config": {}},
        "recovery": {"enabled": False, "checks": []}
    }

@pytest.fixture
def mock_project_with_misfit(tmp_path, mock_config_dict):
    """
    Creates a project with a file containing a misfit function.
    """
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    models_file = project_path / "models.py"
    models_file.write_text(
        "class User:\n"
        "    pass\n\n"
        "def format_user_name(user):\n"
        "    # This is a utility function and doesn't belong here.\n"
        "    return f\"Formatted: {user}\""
    )

    utils_file = project_path / "utils.py"
    utils_file.write_text("# Utility functions")

    # Create pforge.toml
    config_path = project_path / "pforge.toml"
    with open(config_path, "w") as f:
        toml.dump(mock_config_dict, f)

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=project_path, check=True, capture_output=True)

    return project_path

from pforge.orchestrator.core import Orchestrator
from pforge.project import Project
from pforge.config import Config
from pforge.orchestrator.signals import Message, MsgType

@pytest.mark.asyncio
@pytest.mark.e2e
@patch("pforge.agents.planner_agent.PlannerAgent._add_refactor_task")
@patch("pforge.agents.misfit_agent.MisfitAgent.on_tick", new_callable=AsyncMock)
async def test_misfit_refactoring_e2e(mock_misfit_on_tick, mock_add_refactor_task, mock_project_with_misfit):
    """
    Tests that a misfit is detected and a refactoring task is created in an E2E workflow.
    """
    project_path = mock_project_with_misfit
    project = Project(project_path)
    config = Config.load(path=project_path / "pforge.toml")

    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()
    bus = orchestrator.bus

    # Mock the MisfitAgent's on_tick to directly publish a MISFIT_DETECTED message
    # This avoids dealing with LLM mocks and focuses on the agent interaction.
    async def fake_misfit_tick():
        misfit_message = Message(
            type=MsgType.MISFIT_DETECTED,
            payload={
                "file_path": "models.py",
                "symbol": "format_user_name",
                "suggestion": "utils.py",
            }
        )
        await bus.publish(MsgType.MISFIT_DETECTED.value, misfit_message)
    mock_misfit_on_tick.side_effect = fake_misfit_tick

    # --- Run the orchestrator for a few ticks ---
    # Get the MisfitAgent and PlannerAgent to run their on_tick methods
    misfit_agent = next(a for a in orchestrator.agents if a.name == "misfit")
    planner_agent = next(a for a in orchestrator.agents if a.name == "planner")

    await misfit_agent.on_tick()
    await planner_agent.on_tick()

    # --- Assertions ---
    # Check that the planner's _add_refactor_task method was called
    mock_add_refactor_task.assert_called_once()

    # Check the payload it was called with
    call_args = mock_add_refactor_task.call_args[0][0] # Get the first positional argument
    assert call_args["file_path"] == "models.py"
    assert call_args["symbol"] == "format_user_name"
    assert call_args["suggestion"] == "utils.py"
