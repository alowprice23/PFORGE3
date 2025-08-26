from __future__ import annotations
import asyncio
import orjson
import logging

import socketio
from pforge.messaging.redis_stream import get_redis_client

logger = logging.getLogger(__name__)

# --- Socket.IO Server Setup ---
# We use Socket.IO for its robustness, automatic reconnection, and ease of use.
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*", # Allow all origins for local dev
    logger=False,
    engineio_logger=False
)

# --- Background Task for Forwarding Redis Events ---
async def redis_event_forwarder():
    """
    A long-running task that listens to the global AMP event stream on Redis
    and forwards messages to all connected WebSocket clients.
    """
    redis_client = get_redis_client()
    # We use a simple pub/sub model here for broadcasting, but for a more
    # robust system, you might use streams with consumer groups.
    pubsub = redis_client.pubsub()

    # Subscribe to the channel where all AMP events are broadcast
    await pubsub.psubscribe("pforge:amp:global:*")

    logger.info("WebSocket forwarder is listening to Redis pub/sub channels.")

    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "pmessage":
                # The actual message data is in the 'data' field
                event_data = orjson.loads(message["data"])

                # Emit the event to all connected WebSocket clients
                # The event name can be the AMP event type for easy client-side routing
                event_type = event_data.get("type", "unknown_event")
                await sio.emit(event_type, event_data)

            await asyncio.sleep(0.01) # Prevent tight loop
        except Exception as e:
            logger.error(f"Error in WebSocket event forwarder: {e}")
            await asyncio.sleep(5) # Wait before retrying on error


# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

# --- FastAPI Integration ---
# Create an ASGI app that can be mounted onto the main FastAPI app.
socket_app = socketio.ASGIApp(sio)

# Start the background task when the app is mounted.
@sio.on('connect')
async def on_startup(sid, environ):
    # A bit of a hack to start the background task only once
    if not hasattr(sio, "redis_forwarder_task"):
        sio.redis_forwarder_task = asyncio.create_task(redis_event_forwarder())

def attach_ws_to_app(app):
    """Mounts the Socket.IO app on the main FastAPI application."""
    app.mount("/ws", socket_app)
