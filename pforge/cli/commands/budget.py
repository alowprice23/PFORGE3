# pforge/cli/commands/budget.py
"""
This module contains the budget command for the pForge CLI.
"""

import typer

app = typer.Typer()

@app.command()
def budget(amount: int):
    """Sets the budget."""
    print(f"Setting budget to: {amount}")

if __name__ == "__main__":
    app()
