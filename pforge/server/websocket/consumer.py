from __future__ import annotations
import asyncio
import orjson
import logging

import socketio

logger = logging.getLogger(__name__)

# --- Socket.IO Server Setup ---
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False
)

# --- Background Task for Forwarding Events ---
async def event_forwarder():
    """
    (Placeholder) A long-running task that would forward events
    to all connected WebSocket clients.
    """
    while True:
        await asyncio.sleep(5)

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

# --- FastAPI Integration ---
socket_app = socketio.ASGIApp(sio)

@sio.on('connect')
async def on_startup(sid, environ):
    if not hasattr(sio, "forwarder_task"):
        sio.forwarder_task = asyncio.create_task(event_forwarder())

def attach_ws_to_app(app):
    """Mounts the Socket.IO app on the main FastAPI application."""
    app.mount("/ws", socket_app)
