from __future__ import annotations
import time
from typing import Optional

from redis.asyncio import Redis

class BudgetExceededError(Exception):
    """Raised when an operation would exceed the allocated token budget."""
    pass

class BudgetMeter:
    """
    Tracks and enforces token budgets for LLM API calls using a Redis-compatible API.
    This implementation is designed for local-first operation, using fakeredis.
    """
    STREAM_PREFIX = "pforge:budget:"

    def __init__(self, tenant: str, daily_quota_tokens: int, redis_client: Redis):
        if not redis_client:
            raise ValueError("A Redis client instance is required.")
        self.tenant = tenant
        self.daily_quota = daily_quota_tokens
        self.redis = redis_client

    def _get_daily_key(self) -> str:
        """Generates a Redis key for the current day."""
        today = time.strftime("%Y-%m-%d")
        return f"{self.STREAM_PREFIX}{self.tenant}:{today}"

    async def spend(self, tokens: int) -> bool:
        """
        Atomically checks if spending `tokens` would exceed the daily quota
        and, if not, increments the daily usage. This version avoids Lua scripts
        and uses a transaction pipeline compatible with fakeredis.

        Returns:
            bool: True if the spend was successful, False otherwise.
        """
        key = self._get_daily_key()

        # Use a transaction (MULTI/EXEC) to make the read-modify-write atomic.
        # fakeredis supports this pattern.
        async with self.redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(key)
                current_usage = await pipe.get(key)
                current_usage = int(current_usage) if current_usage else 0

                if current_usage + tokens > self.daily_quota:
                    await pipe.unwatch()
                    return False

                # Start the transaction
                pipe.multi()
                pipe.incrby(key, tokens)
                pipe.expire(key, 86400) # Expire in 24 hours

                await pipe.execute()
                return True
            except self.redis.exceptions.WatchError:
                # The key was modified by another client after we WATCHed it.
                # In a high-concurrency scenario, we might retry here.
                # For our local agent model, this is unlikely to happen.
                return False

    async def get_today_usage(self) -> int:
        """Returns the total tokens used in the current 24-hour period."""
        key = self._get_daily_key()
        usage = await self.redis.get(key)
        return int(usage) if usage else 0
