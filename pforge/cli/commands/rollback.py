# pforge/cli/commands/rollback.py
"""
This module contains the rollback command for the pForge CLI.
"""

import typer

app = typer.Typer()

@app.command()
def rollback():
    """Rolls back the last action."""
    print("Rolling back last action.")

if __name__ == "__main__":
    app()
