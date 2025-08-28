import typer
from pforge.orchestrator.state_bus import StateBus
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Check the status of the pForge system.")
console = Console()

@app.command(name="show", help="Display a summary of the pForge system's current status and metrics.")
def show_status():
    """
    Fetches the latest state from the StateBus and displays it in a table.
    """
    state_bus = StateBus()
    state = state_bus.get_latest_state()

    table = Table(title="pForge System Status")
    table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Tick", str(state.tick))
    table.add_row("Efficiency (E)", f"{state.efficiency:.2f}")
    table.add_row("Entropy (H)", f"{state.entropy:.2f}")
    table.add_row("Gaps", str(state.gaps))
    table.add_row("Misfits", str(state.misfits))
    table.add_row("False Pieces", str(state.false_pieces))
    table.add_row("Risk", f"{state.risk:.2f}")
    table.add_row("Backtracks", str(state.backtracks))
    table.add_row("Phi (False Pieces Removed)", str(state.phi))

    console.print(table)

if __name__ == "__main__":
    app()
