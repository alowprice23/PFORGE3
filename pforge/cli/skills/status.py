import typer
import httpx
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Check the status of the pForge system.")
console = Console()

API_BASE_URL = "http://localhost:8000"

@app.command(name="show", help="Display a summary of the pForge system's current status and metrics.")
def show_status():
    """
    Fetches the latest metrics from the pForge server and displays them
    in a formatted table.
    """
    try:
        response = httpx.get(f"{API_BASE_URL}/metrics", timeout=5.0)
        response.raise_for_status()

        metrics = _parse_prometheus_metrics(response.text)

        table = Table(title="pForge System Status")
        table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        # Display key metrics
        table.add_row("Efficiency (E)", metrics.get("pforge_efficiency", "N/A"))
        table.add_row("Entropy (H)", metrics.get("pforge_entropy", "N/A"))
        table.add_row("Open Gaps", metrics.get("pforge_gaps_total", "N/A"))
        table.add_row("Active Misfits", metrics.get("pforge_misfits_total", "N/A"))
        table.add_row("Tokens Used (Total)", metrics.get("pforge_tokens_used_total", "N/A"))
        table.add_row("Patches Applied", metrics.get("pforge_patches_applied_total", "N/A"))
        table.add_row("Rollbacks", metrics.get("pforge_rollbacks_total", "N/A"))

        console.print(table)

    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to the pForge server at {API_BASE_URL}.")
        console.print(f"Details: {e}")
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error:[/bold red] Server returned an error (Status {e.response.status_code}).")

def _parse_prometheus_metrics(text: str) -> dict:
    """
    A simple parser for the Prometheus text format.
    """
    metrics = {}
    for line in text.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            # For simplicity, we ignore labels for now.
            metric_name = parts[0].split('{')[0]
            value = parts[1]
            metrics[metric_name] = value
    return metrics

if __name__ == "__main__":
    app()
