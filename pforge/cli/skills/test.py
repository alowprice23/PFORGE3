import typer
import subprocess
from rich.console import Console

app = typer.Typer(help="Run tests for the pForge system.")
console = Console()

@app.command(name="run", help="Run the pytest test suite.")
def run_tests():
    """
    Executes the pytest test suite and prints the output to the console.
    """
    try:
        console.print("[bold cyan]Running pytest test suite...[/bold cyan]")
        result = subprocess.run(
            ["python", "-m", "pytest"],
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code
        )
        console.print(result.stdout)
        if result.stderr:
            console.print("[bold red]Errors:[/bold red]")
            console.print(result.stderr)
    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] 'python' command not found. Is Python installed and in your PATH?")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")

if __name__ == "__main__":
    app()
