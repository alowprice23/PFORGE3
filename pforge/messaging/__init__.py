"""
The Messaging package provides the schema and transport abstraction for all
inter-agent communication in the pForge system.

Modules:
- amp: Defines the canonical `AMPMessage` data model for all events.
- redis_stream: Provides a high-level, asynchronous wrapper for the Redis
  Streams message bus, with a graceful fallback to `fakeredis` for
  local-only operation.
"""

from .amp import AMPMessage
from .redis_stream import get_redis_client, stream_add, stream_read_group, stream_ack

__all__ = [
    "AMPMessage",
    "get_redis_client",
    "stream_add",
    "stream_read_group",
    "stream_ack",
]
