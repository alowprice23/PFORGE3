# pforge/cli/commands/spawn.py
"""
This module contains the spawn command for the pForge CLI.
"""

import typer

app = typer.Typer()

@app.command()
def spawn(agent: str):
    """Spawns an agent."""
    print(f"Spawning agent: {agent}")

if __name__ == "__main__":
    app()
