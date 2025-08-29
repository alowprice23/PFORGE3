"""
The Server package provides the primary API and web service layer for pForge.

It is the main entry point for all external clients, including the web UI,
the command-line tool, and any potential third-party integrations.
"""

from .app import app

__all__ = ["app"]
