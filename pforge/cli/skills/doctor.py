import typer
import asyncio
import logging
from pathlib import Path

from pforge.config import Config
from pforge.project import Project
from pforge.orchestrator.core import Orchestrator

app = typer.Typer(
    name="doctor",
    help="Runs the end-to-end diagnosis and repair workflow on a project.",
)

logger = logging.getLogger(__name__)

async def run_doctor_flow(project_path: Path, test_node_id: str | None = None):
    """Sets up and runs the orchestrator for the doctor command."""

    if test_node_id:
        typer.echo(f"🩺 Starting pForge Doctor on: {project_path} to fix test: {test_node_id}")
    else:
        typer.echo(f"🩺 Starting pForge Doctor on: {project_path}")

    try:
        config = Config.load(project_path / "pforge.toml")
    except FileNotFoundError:
        typer.echo("🚨 Error: pforge.toml not found in the current directory.")
        typer.echo("Please create one or run `pforge init`.")
        raise typer.Exit(code=1)

    project = Project(project_path)

    orchestrator = Orchestrator(config, project, puzzle_id=test_node_id)
    orchestrator.setup_agents()

    # The orchestrator will now run until the puzzle is solved or it fails.
    print("Running orchestrator...")
    success = await orchestrator.run()
    print("Orchestrator finished.")

    if success:
        typer.echo("✅ Doctor workflow complete: Puzzle solved!")
    else:
        typer.echo("❌ Doctor workflow failed: Could not solve the puzzle.")
        raise typer.Exit(code=1)


@app.command()
def run(
    project_path: Path = typer.Argument(
        ".",
        help="The path to the project directory to be analyzed.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    test_node_id: str = typer.Option(
        None,
        "--test-node-id",
        "-t",
        help="The specific test node ID to target for fixing.",
    )
):
    """
    Analyzes a project, proposes a fix for a bug, and applies it.
    """
    try:
        asyncio.run(run_doctor_flow(project_path, test_node_id))
    except KeyboardInterrupt:
        typer.echo("\nGracefully shutting down pForge Doctor...")
    except Exception as e:
        logger.error(f"An error occurred during the doctor workflow: {e}", exc_info=True)
        typer.echo(f"🚨 Error: {e}")
        raise typer.Exit(code=1)
