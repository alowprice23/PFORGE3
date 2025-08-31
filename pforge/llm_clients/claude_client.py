from __future__ import annotations
import os
import logging
from typing import List, Dict, Any

import anthropic

from .retry import retry_llm
from .budget_meter import BudgetMeter, BudgetExceededError

logger = logging.getLogger(__name__)

class ClaudeClient:
    """A client for interacting with Anthropic's Claude models, with budget and retry support."""

    def __init__(self, api_key: str | None, model: str = "claude-3-sonnet-20240229", budget_meter: BudgetMeter | None = None):
        self.model = model
        self.budget_meter = budget_meter

        if not api_key:
            logger.warning("Anthropic API key not provided. Client will operate in offline/stub mode.")
            self.client = None
        else:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)

    @retry_llm()
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generates a response from a Claude model.

        Args:
            messages: A list of messages in the chat format. Note that Claude expects
                      alternating user/assistant roles.
            **kwargs: Additional arguments to pass to the Anthropic API.

        Returns:
            The string content of the assistant's reply.

        Raises:
            BudgetExceededError: If the estimated token usage exceeds the budget.
            anthropic.APIError: If the API call fails after retries.
        """
        if not self.client:
            logger.info("Simulating Claude call (offline mode).")
            return "```python\ndef some_claude_fix():\n    return True\n```"

        # Estimate token usage for budget check
        estimated_prompt_tokens = sum(len(m.get("content", "")) for m in messages) // 3
        max_completion_tokens = kwargs.get("max_tokens", 1024)
        estimated_total = estimated_prompt_tokens + max_completion_tokens

        if self.budget_meter:
            if not await self.budget_meter.spend(estimated_total):
                raise BudgetExceededError(f"Claude call would exceed budget. Estimated tokens: {estimated_total}")

        logger.info("Making Claude call to model '%s'...", self.model)

        # Claude's API has a slightly different structure for the `messages` parameter
        response = await self.client.messages.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

        return response.content[0].text or ""
