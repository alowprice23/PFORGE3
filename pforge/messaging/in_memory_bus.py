from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import Dict, List, Any

import fakeredis.aioredis

class InMemoryBus:
    """
    An in-memory, topic-based, pub/sub message bus using asyncio.Queue.
    Supports multiple subscribers per topic.
    Also provides a fakeredis instance for components that need a Redis-like API.
    """
    def __init__(self):
        # A dictionary mapping a topic to a list of subscriber queues
        self.topics: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        # A dictionary mapping a subscriber's name to its personal queue
        self.subscriber_queues: Dict[str, asyncio.Queue] = {}
        # A shared fakeredis client for components like BudgetMeter
        self.redis_client = fakeredis.aioredis.FakeRedis()

    def _get_or_create_subscriber_queue(self, subscriber_name: str) -> asyncio.Queue:
        """Gets or creates a queue for a given subscriber."""
        if subscriber_name not in self.subscriber_queues:
            self.subscriber_queues[subscriber_name] = asyncio.Queue()
        return self.subscriber_queues[subscriber_name]

    def subscribe(self, subscriber_name: str, topic: str):
        """
        Subscribes a named subscriber to a topic.
        The subscriber will receive messages published to this topic in its personal queue.
        """
        queue = self._get_or_create_subscriber_queue(subscriber_name)
        if queue not in self.topics[topic]:
            self.topics[topic].append(queue)

    def subscribe_to_topic(self, subscriber_name: str, topic: str, callback: callable):
        """
        A convenience method for subscribing with a callback.
        This is useful for testing and simple listeners.
        A real agent would use the get() method in a loop.
        """
        async def listener():
            queue = self._get_or_create_subscriber_queue(subscriber_name)
            self.topics[topic].append(queue)
            while True:
                message = await queue.get()
                await callback(message)

        asyncio.create_task(listener())


    async def publish(self, topic: str, message: Any):
        """Publishes a message to all subscribers of a topic."""
        if topic in self.topics:
            for queue in self.topics[topic]:
                await queue.put(message)

    async def get(self, subscriber_name: str, timeout: float | None = None) -> Any | None:
        """
        Waits for and retrieves a message from a subscriber's personal queue.
        Returns None if the timeout is reached.
        """
        queue = self._get_or_create_subscriber_queue(subscriber_name)
        try:
            if timeout:
                return await asyncio.wait_for(queue.get(), timeout=timeout)
            else:
                return await queue.get()
        except asyncio.TimeoutError:
            return None

    async def start(self):
        """
        The bus itself doesn't need a start/stop loop, but this method is kept
        for API compatibility with the Orchestrator's expectation.
        """
        # In a more complex implementation, this could manage heartbeats or cleanup.
        pass
