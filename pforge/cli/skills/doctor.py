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

async def run_doctor_flow(project_path: Path):
    """Sets up and runs the orchestrator for the doctor command."""

    typer.echo(f"🩺 Starting pForge Doctor on: {project_path}")

    try:
        config = Config.load()
    except FileNotFoundError:
        typer.echo("🚨 Error: pforge.toml not found in the current directory.")
        typer.echo("Please create one or run `pforge init`.")
        raise typer.Exit(code=1)

    project = Project(project_path)

    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    # In a real scenario, the orchestrator might run indefinitely or until a
    # specific condition is met. For this CLI command, we might run it for a
    # fixed duration, for a single loop, or until a fix is found.
    # Here, we'll just run it and let the user stop with Ctrl+C.
    await orchestrator.run()

    typer.echo("✅ Doctor workflow complete.")


@app.command()
def run(
    project_path: Path = typer.Argument(
        ".",
        help="The path to the project directory to be analyzed.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    )
):
    """
    Analyzes a project, proposes a fix for a bug, and applies it.
    """
    try:
        asyncio.run(run_doctor_flow(project_path))
    except KeyboardInterrupt:
        typer.echo("\nGracefully shutting down pForge Doctor...")
    except Exception as e:
        logger.error(f"An error occurred during the doctor workflow: {e}", exc_info=True)
        typer.echo(f"🚨 Error: {e}")
        raise typer.Exit(code=1)
