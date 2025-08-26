"""
This package contains the real-time communication endpoints for the server,
primarily using WebSockets or other push-based technologies.
"""

from .consumer import attach_ws_to_app, sio

__all__ = ["attach_ws_to_app", "sio"]
