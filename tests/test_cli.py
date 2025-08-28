from typer.testing import CliRunner
from pforge.cli.main import app

runner = CliRunner()

def test_app_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage: pforge [OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "An agentic, self-improving CLI for the pForge puzzle-solving system." in result.stdout

import pytest
from pathlib import Path
from pforge.cli.skills.doctor import run_doctor_flow

@pytest.mark.asyncio
async def test_doctor_run():
    # Create a dummy project path
    project_path = Path("demo_buggy/")
    project_path.mkdir(exist_ok=True)
    (project_path / "main.py").write_text("def hello_world()\n    print('Hello, World!')")

    await run_doctor_flow(project_path)
