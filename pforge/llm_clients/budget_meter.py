from __future__ import annotations
import time
from typing import Optional

class BudgetExceededError(Exception):
    """Raised when an operation would exceed the allocated token budget."""
    pass

class BudgetMeter:
    """
    Tracks and enforces token budgets for LLM API calls.
    This is a simple in-memory implementation for local-only operation.
    """
    def __init__(self, tenant: str, daily_quota: int):
        self.tenant = tenant
        self.daily_quota = daily_quota
        self.usage: dict[str, int] = {}
        self._reset_today()

    def _today_key(self) -> str:
        """Generates a key for the current day."""
        return time.strftime("%Y-%m-%d")

    def _reset_today(self):
        """Resets the usage if the day has changed."""
        today = self._today_key()
        if today not in self.usage:
            self.usage = {today: 0}

    def spend(self, tokens: int) -> bool:
        """
        Checks if spending `tokens` would exceed the daily quota and, if not,
        increments the daily usage.
        """
        self._reset_today()
        today = self._today_key()

        if self.usage[today] + tokens > self.daily_quota:
            return False

        self.usage[today] += tokens
        return True

    def get_today_usage(self) -> int:
        """Returns the total tokens used in the current 24-hour period."""
        self._reset_today()
        today = self._today_key()
        return self.usage.get(today, 0)
