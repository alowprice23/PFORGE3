from __future__ import annotations
import os
from typing import Dict, List, Tuple

import redis.asyncio as redis
from redis.exceptions import ResponseError
import fakeredis.aioredis
from .amp import AMPMessage
import logging

logger = logging.getLogger(__name__)

# A singleton client instance to be shared across the application.
_redis_client = None

def get_redis_client() -> redis.Redis:
    """
    Initializes and returns a Redis client.

    If the REDIS_URL environment variable is set, it connects to a real Redis
    server. Otherwise, it transparently falls back to a `fakeredis` in-memory
    instance, allowing for dependency-free local execution.
    """
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            _redis_client = redis.from_url(redis_url, decode_responses=False)
        else:
            # The `decode_responses=False` is important to handle raw bytes,
            # which orjson prefers for performance.
            _redis_client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    return _redis_client

async def stream_add(
    redis_client: redis.Redis,
    stream_name: str,
    message: AMPMessage,
    max_len: int = 1000
):
    """
    Adds a message to a Redis stream, serializing it to JSON.

    Args:
        redis_client: The Redis client instance.
        stream_name: The name of the stream to add the message to.
        message: The AMPMessage object to add.
        max_len: The approximate maximum length of the stream.
    """
    logger.info(f"Adding message of type {message.type} to stream {stream_name}")
    payload = {"amp_json": message.to_json()}
    await redis_client.xadd(stream_name, payload, maxlen=max_len, approximate=True) # type: ignore

async def stream_read_group(
    redis_client: redis.Redis,
    group_name: str,
    consumer_name: str,
    streams: Dict[str, str],
    count: int = 10,
    block_ms: int = 2000
) -> List[Tuple[str, str, AMPMessage]]:
    """
    Reads messages from one or more streams using a consumer group.

    This ensures that messages are distributed among consumers and can be
    acknowledged, providing more robust message processing.

    Args:
        redis_client: The Redis client instance.
        group_name: The name of the consumer group.
        consumer_name: The name of the consumer processing the messages.
        streams: A dictionary mapping stream names to the IDs to read from
                 (e.g., `'>'` for new messages).
        count: The maximum number of messages to read.
        block_ms: The maximum time in milliseconds to block waiting for messages.

    Returns:
        A list of tuples, each containing (stream_name, message_id, AMPMessage).
    """
    # Ensure the consumer group exists for all streams.
    for stream in streams.keys():
        try:
            await redis_client.xgroup_create(stream, group_name, id="0", mkstream=True)
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    # Read from the stream using the consumer group.
    response = await redis_client.xreadgroup(
        group_name,
        consumer_name,
        streams, # type: ignore
        count=count,
        block=block_ms
    )

    logger.info(f"xreadgroup response: {response}")

    if not response:
        return []

    messages = []
    for stream_name, entries in response:
        for message_id, fields in entries:
            amp_json = fields.get(b'amp_json')
            if not amp_json:
                logger.warning(f"Message {message_id} in stream {stream_name} is missing 'amp_json' field. Fields: {fields}")
                continue
            amp_message = AMPMessage.from_json(amp_json)
            messages.append((stream_name.decode('utf-8'), message_id.decode('utf-8'), amp_message))

    return messages

async def stream_ack(
    redis_client: redis.Redis,
    stream_name: str,
    group_name: str,
    message_id: str
):
    """
    Acknowledges that a message has been successfully processed by a consumer.
    """
    await redis_client.xack(stream_name, group_name, message_id)
