from __future__ import annotations
import asyncio
import orjson
import time
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, Request, HTTPException
from starlette.responses import StreamingResponse

router = APIRouter()

@router.post(
    "/nl",
    summary="Submit a natural language message",
    tags=["Chat"]
)
async def post_natural_language_message(request: Request, payload: Dict[str, str]):
    """
    Accepts a natural language message from a user.
    (This is a placeholder implementation)
    """
    message_text = payload.get("msg", "").strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Field 'msg' cannot be empty.")

    user_id = getattr(request.state, "user", "anonymous")

    return {"status": "message_queued", "user": user_id, "reply": "This is a placeholder response."}

async def event_stream_generator(request: Request) -> AsyncGenerator[str, None]:
    """
    A generator function for Server-Sent Events (SSE).
    (This is a placeholder implementation)
    """
    while True:
        if await request.is_disconnected():
            break

        sse_event = f"event: message\n"
        sse_event += f"data: {orjson.dumps({'message': 'placeholder event'}).decode('utf-8')}\n\n"
        yield sse_event
        await asyncio.sleep(5)


@router.get(
    "/events",
    summary="Subscribe to real-time server events",
    tags=["Chat"]
)
async def get_server_events(request: Request):
    """
    An SSE endpoint that allows clients to receive a real-time stream of events.
    """
    return StreamingResponse(event_stream_generator(request), media_type="text/event-stream")
