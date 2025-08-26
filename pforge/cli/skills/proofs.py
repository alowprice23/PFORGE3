import typer
import httpx
import orjson
from rich.console import Console
from rich.json import JSON

app = typer.Typer(help="Inspect and manage pForge proof bundles.")
console = Console()

API_BASE_URL = "http://localhost:8000"

@app.command(name="show", help="Fetch and display a proof bundle by its operation ID.")
def show_proof(
    op_id: str = typer.Argument(..., help="The operation ID of the proof to display."),
):
    """
    Connects to the pForge server to retrieve and display the details of
    a specific, signed proof bundle.
    """
    try:
        url = f"{API_BASE_URL}/api/proofs/{op_id}"
        console.print(f"Fetching proof from [cyan]{url}[/cyan]...")

        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()

        # The response should be the full AMP message containing the proof
        amp_message = response.json()

        # Use rich's JSON rendering for a nice, syntax-highlighted display
        rich_json = JSON(orjson.dumps(amp_message, option=orjson.OPT_INDENT_2).decode('utf-8'))
        console.print(rich_json)

    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to the pForge server.")
        console.print(f"Details: {e}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[bold red]Error:[/bold red] No proof found with operation ID '{op_id}'.")
        else:
            console.print(f"[bold red]Error:[/bold red] Server returned an error (Status {e.response.status_code}).")
            console.print(f"Response: {e.response.text}")

if __name__ == "__main__":
    app()
