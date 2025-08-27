from __future__ import annotations
import asyncio
from .amp import AMPMessage

class InMemoryBus:
    """
    A simple in-memory message bus using asyncio.Queue.
    """
    def __init__(self):
        self.queues = {
            "pforge:amp:global:events": asyncio.Queue()
        }

    def get_queue(self, stream_name: str) -> asyncio.Queue:
        """
        Gets a queue for a given stream name. If the queue does not exist,
        it is created.
        """
        if stream_name not in self.queues:
            self.queues[stream_name] = asyncio.Queue()
        return self.queues[stream_name]

    async def publish(self, stream_name: str, message: AMPMessage):
        """
        Publishes a message to a specific stream (queue).
        """
        queue = self.get_queue(stream_name)
        await queue.put(message)

    async def subscribe(self, stream_name: str) -> AMPMessage:
        """
        Subscribes to a stream and waits for a message.
        """
        queue = self.get_queue(stream_name)
        return await queue.get()
