import typer
from pforge.memory.constellation import Constellation
from rich.console import Console
from rich.json import JSON
from pathlib import Path
import os
import json

app = typer.Typer(help="Inspect and manage pForge proof bundles.")
console = Console()

@app.command(name="show", help="Fetch and display a proof bundle by its operation ID.")
def show_proof(
    op_id: int = typer.Argument(..., help="The operation ID of the proof to display."),
):
    """
    Connects to the local Constellation database to retrieve and display
    the details of a specific proof bundle.
    """
    db_path_str = os.getenv("PFORGE_DB_PATH", str(Path.home() / ".pforge" / "constellation.sqlite"))
    db_path = Path(db_path_str)

    if not db_path.exists():
        console.print(f"[bold red]Error:[/bold red] Constellation database not found at {db_path}")
        return

    memory = Constellation(db_path=db_path)
    route = memory.get_route(op_id)

    if not route:
        console.print(f"[bold red]Error:[/bold red] No proof found with operation ID '{op_id}'.")
        return

    # Use rich's JSON rendering for a nice, syntax-highlighted display
    rich_json = JSON(json.dumps(route, indent=2))
    console.print(rich_json)

if __name__ == "__main__":
    app()
