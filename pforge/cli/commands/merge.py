# pforge/cli/commands/merge.py
"""
This module contains the merge command for the pForge CLI.
"""

import typer

app = typer.Typer()

@app.command()
def merge(branch: str):
    """Merges a branch."""
    print(f"Merging branch: {branch}")

if __name__ == "__main__":
    app()
