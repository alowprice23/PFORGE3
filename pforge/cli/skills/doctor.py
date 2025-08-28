import typer
import asyncio
from pforge.agentic.loop import AgenticLoop, Observation
from pforge.memory.constellation import Constellation
from pathlib import Path
import os

app = typer.Typer(
    name="doctor",
    help="Runs the end-to-end diagnosis and repair workflow on a project.",
)

async def run_doctor_flow(project_path: Path):
    """Sets up and runs the agentic loop for the doctor command."""
    typer.echo(f"🩺 Starting pForge Doctor on: {project_path}")

    db_path_str = os.getenv("PFORGE_DB_PATH", str(Path.home() / ".pforge" / "constellation.sqlite"))
    db_path = Path(db_path_str)

    memory = Constellation(db_path=db_path)
    agentic_loop = AgenticLoop(memory=memory)

    obs = Observation.from_env(target_path=project_path)
    agentic_loop.plan_act_learn(obs, doctor_mode=True)

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
        typer.echo(f"🚨 Error: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
