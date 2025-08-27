from __future__ import annotations
import logging
from typing import Dict, List, Tuple

from redis.asyncio import Redis
from .amp import AMPMessage

log = logging.getLogger("messaging.redis")

async def stream_read_group(
    redis: Redis,
    group_name: str,
    consumer_name: str,
    streams: Dict[str, str],
    count: int = 10,
    block_ms: int = 1000,
) -> List[Tuple[str, str, AMPMessage]]:
    """
    Reads from a stream using a consumer group.
    """
    if not streams:
        return []

    try:
        # ">" means read new messages
        response = await redis.xreadgroup(
            group_name, consumer_name, streams, count=count, block=block_ms
        )
    except Exception as e:
        log.error(f"Error reading from stream group {group_name}: {e}")
        # Try to create the group if it doesn't exist
        for stream_name in streams.keys():
            try:
                await redis.xgroup_create(stream_name, group_name, id="$", mkstream=True)
                log.info(f"Created group {group_name} for stream {stream_name}")
            except Exception as create_e:
                # Group might already exist, which is fine.
                if "BUSYGROUP" not in str(create_e):
                    log.error(f"Failed to create group {group_name} for stream {stream_name}: {create_e}")
        return []


    messages: List[Tuple[str, str, AMPMessage]] = []
    if response:
        for stream, entries in response:
            for msg_id, fields in entries:
                raw = fields.get(b"json")
                if raw:
                    messages.append((stream.decode(), msg_id.decode(), AMPMessage.from_json(raw.decode())))
    return messages

async def stream_ack(
    redis: Redis,
    stream: str,
    group_name: str,
    msg_id: str,
) -> None:
    """Acknowledges a message in a consumer group."""
    await redis.xack(stream, group_name, msg_id)
