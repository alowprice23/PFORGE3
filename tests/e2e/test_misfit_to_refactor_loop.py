"""
This file contains the E2E test for the misfit-to-refactor loop.
"""
import pytest
from pathlib import Path
import shutil

# It's better to have a helper function to set up the project
def setup_test_project(tmp_path: Path):
    """Sets up a test project with a misfit function."""
    project_path = tmp_path / "misfit_project"
    project_path.mkdir()

    # Create pforge.toml
    (project_path / "pforge.toml").write_text("""
[project]
name = "misfit_project"
    """)

    # Create app structure
    app_path = project_path / "my_app"
    app_path.mkdir()

    (app_path / "__init__.py").touch()

    # Create models.py with a misfit
    (app_path / "models.py").write_text("""
class User:
    def __init__(self, name: str):
        self.name = name

def format_date(date): # This is a misfit
    return date.strftime("%Y-%m-%d")
    """)

    # Create an empty utils.py as a potential destination
    (app_path / "utils.py").write_text("# Utility functions")

    return project_path


@pytest.mark.asyncio
async def test_misfit_to_refactor_loop(tmp_path: Path):
    """
    Tests that a misfit function is detected and moved to the correct file.
    """
    project_path = setup_test_project(tmp_path)

    # This is a placeholder for now. We need to implement the orchestrator run
    # and the assertions. For now, we'll just check that the setup is correct.
    assert (project_path / "my_app" / "models.py").exists()
    assert (project_path / "my_app" / "utils.py").exists()

    # In a real test, we would do something like this:
    # from pforge.orchestrator.core import Orchestrator
    # from pforge.config import Config
    # from pforge.project import Project
    #
    # config = Config.load(project_path / "pforge.toml")
    # project = Project(project_path)
    # orchestrator = Orchestrator(config, project)
    # orchestrator.setup_agents()
    # await orchestrator.run()
    #
    # models_content = (project_path / "my_app" / "models.py").read_text()
    # utils_content = (project_path / "my_app" / "utils.py").read_text()
    #
    # assert "def format_date" not in models_content
    # assert "def format_date" in utils_content
