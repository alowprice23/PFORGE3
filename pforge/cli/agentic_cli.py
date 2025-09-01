# pforge/cli/agentic_cli.py
"""
This module contains the agentic CLI for pForge.
"""

import typer

app = typer.Typer()

@app.command()
def main():
    """The main command for the agentic CLI."""
    pass

if __name__ == "__main__":
    app()
