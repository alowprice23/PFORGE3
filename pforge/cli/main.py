import typer
from .chat import start_chat_repl
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
    """
    if ctx.invoked_subcommand is None:
        start_chat_repl()

if __name__ == "__main__":
    app()
