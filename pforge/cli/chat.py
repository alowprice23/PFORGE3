import typer
from pforge.agentic.loop import AgenticLoop
from pforge.memory.constellation import Constellation
from pathlib import Path
import os

def start_chat_repl():
    """Starts the interactive chat REPL for the pForge CLI."""
    typer.echo("Welcome to the pForge Agentic CLI. Type 'exit' to quit.")

    db_path_str = os.getenv("PFORGE_DB_PATH", str(Path.home() / ".pforge" / "constellation.sqlite"))
    db_path = Path(db_path_str)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    memory = Constellation(db_path=db_path)
    agentic_loop = AgenticLoop(memory=memory)

    while True:
        try:
            user_input = typer.prompt("You")
            if user_input.lower() == "exit":
                break

            response = agentic_loop.process_input_sync(user_input)
            typer.echo(f"pForge: {response}")

        except (KeyboardInterrupt, EOFError):
            break

    typer.echo("Exiting pForge CLI. Goodbye!")
