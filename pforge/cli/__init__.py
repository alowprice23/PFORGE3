"""
The CLI package provides the primary command-line interface for pForge.

It is designed as an "agentic CLI", meaning it is self-aware, learns
from its operations, and can use LLMs to plan and reason about complex
workflows.

Modules:
- main: The main `pforge` Typer application entry point.
- chat: The interactive REPL for conversational interaction.
- skills: The directory containing the implementation of each discrete command.
- routes: Manages the CLI's knowledge of its own capabilities.
- prompts: Contains the version-controlled prompt templates for LLM interaction.
"""

from .main import app

__all__ = ["app"]
