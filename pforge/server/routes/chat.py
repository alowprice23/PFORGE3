from __future__ import annotations
import asyncio
import orjson
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, Request, HTTPException
from starlette.responses import StreamingResponse

from pforge.messaging.redis_stream import get_redis_client
from pforge.messaging.amp import AMPMessage

router = APIRouter()
redis_client = get_redis_client()

# --- Endpoint for receiving user messages ---
@router.post(
    "/nl",
    summary="Submit a natural language message",
    tags=["Chat"]
)
async def post_natural_language_message(request: Request, payload: Dict[str, str]):
    """
    Accepts a natural language message from a user, validates it, and
    publishes it to the `chat:incoming` stream for the IntentRouterAgent
    to process.
    """
    message_text = payload.get("msg", "").strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Field 'msg' cannot be empty.")

    user_id = getattr(request.state, "user", "anonymous")

    # Create a simple payload for the incoming chat stream
    event_payload = {
        "user": user_id,
        "msg": message_text,
        "ts": time.time(),
    }

    # Publish to the stream that the IntentRouterAgent listens to
    await redis_client.xadd("chat:incoming", {"payload": orjson.dumps(event_payload)})

    return {"status": "message_queued", "user": user_id}

# --- Endpoint for streaming events to the client ---
async def event_stream_generator(request: Request) -> AsyncGenerator[str, None]:
    """
    A generator function for Server-Sent Events (SSE).

    It listens to multiple Redis streams (`chat:outgoing` for direct replies
    and `amp:global:events` for system-wide activity) and pushes them to the
    client.
    """
    # Start reading from the latest message
    streams_to_watch = {
        "chat:outgoing": "$",
        "amp:global:events": "$",
    }

    while True:
        # Check if the client has disconnected
        if await request.is_disconnected():
            break

        # Read from the streams, blocking for a short time
        response = await redis_client.xread(streams_to_watch, count=10, block=1000)

        if response:
            for stream_name_bytes, entries in response:
                stream_name = stream_name_bytes.decode('utf-8')
                for message_id_bytes, fields in entries:
                    # Update the cursor for the next read
                    streams_to_watch[stream_name] = message_id_bytes.decode('utf-8')

                    # Format the event for SSE
                    data_payload = orjson.loads(fields[b'payload'])
                    sse_event = f"event: {stream_name}\n"
                    sse_event += f"data: {orjson.dumps(data_payload).decode('utf-8')}\n\n"
                    yield sse_event

        await asyncio.sleep(0.1)


@router.get(
    "/events",
    summary="Subscribe to real-time server events",
    tags=["Chat"]
)
async def get_server_events(request: Request):
    """
    An SSE endpoint that allows clients to receive a real-time stream of
    chat replies and system-wide AMP events.
    """
    return StreamingResponse(event_stream_generator(request), media_type="text/event-stream")
