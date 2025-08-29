import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer(help="Apply fixes to files.")
console = Console()

@app.command(name="apply", help="Apply a fix to a file.")
def apply_fix(
    file_path: str = typer.Argument(..., help="The path to the file to fix."),
    code: str = typer.Argument(..., help="The new code to write to the file."),
):
    """
    Overwrites the content of a file with the provided code.
    """
    try:
        path = Path(file_path)
        path.write_text(code)
        console.print(f"[bold green]Successfully applied fix to {file_path}[/bold green]")
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] File not found at {file_path}")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")

if __name__ == "__main__":
    app()
