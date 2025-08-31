import typer
from .skills import status, proofs, preflight, doctor

app = typer.Typer(
    name="pforge",
    help="An agentic, self-improving CLI for the pForge puzzle-solving system.",
    add_completion=False,
)

app.add_typer(status.app, name="status")
app.add_typer(proofs.app, name="proofs")
app.add_typer(preflight.app, name="preflight")
app.add_typer(doctor.app, name="doctor")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    pForge CLI: A self-aware, learning interface to the pForge system.

    If no subcommand is provided, this would typically launch the
    interactive chat REPL.
    """
    if ctx.invoked_subcommand is None:
        typer.echo("Welcome to the pForge CLI. Run 'pforge --help' for a list of commands.")
        typer.echo("Interactive chat mode is not yet implemented in this slice.")
        # In the full implementation, this would call a function from `chat.py`
        # to start the REPL loop.
        # from .chat import start_chat_repl
        # start_chat_repl()

if __name__ == "__main__":
    app()
