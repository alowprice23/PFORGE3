import typer
from .skills import status, proofs, preflight, doctor, test, apply_fix

app = typer.Typer(
    name="pforge",
    help="An agentic, self-improving CLI for the pForge puzzle-solving system.",
    add_completion=False,
)

app.add_typer(status.app, name="status")
app.add_typer(proofs.app, name="proofs")
app.add_typer(preflight.app, name="preflight")
app.add_typer(doctor.app, name="doctor")
app.add_typer(test.app, name="test")
app.add_typer(apply_fix.app, name="fix")


@app.command()
def run(
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="The root directory of the project to work on."),
    background: bool = typer.Option(False, "--background", "-b", help="Run the orchestrator in the background."),
):
    """
    Starts the main pForge orchestrator and agent loop.
    """
    import asyncio
    from pforge.orchestrator.core import Orchestrator
    from pforge.config.models import Config
    from pforge.project import Project
    from pathlib import Path

    proj_path = Path(project_dir).resolve()
    typer.echo(f"Starting pForge orchestrator for project at: {proj_path}")

    project = Project(proj_path)
    config = Config.load() # Assumes default config location for now

    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    if background:
        # This is a simplified version of running in the background.
        # A real implementation would use a proper daemonizing process.
        typer.echo("Running orchestrator in the background...")
        asyncio.create_task(orchestrator.run())
        typer.echo("Orchestrator started. You can now interact with it via other commands or the chat interface.")
    else:
        typer.echo("Running orchestrator in the foreground. Press Ctrl+C to exit.")
        asyncio.run(orchestrator.run())


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    pForge CLI: A self-aware, learning interface to the pForge system.

    If no subcommand is provided, this would typically launch the
    interactive chat REPL.
    """
    if ctx.invoked_subcommand is None:
        # If no subcommand is provided, launch the interactive chat REPL.
        from .chat import start_chat_repl
        start_chat_repl()

if __name__ == "__main__":
    app()
