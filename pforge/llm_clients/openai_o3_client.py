from __future__ import annotations
import os
import logging
from typing import List, Dict, Any

import openai

from .retry import retry_llm
from .budget_meter import BudgetMeter, BudgetExceededError

logger = logging.getLogger(__name__)

class OpenAIClient:
    """A client for interacting with OpenAI's models, with budget and retry support."""

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini", budget_meter: BudgetMeter | None = None):
        self.model = model
        self.budget_meter = budget_meter

        if not api_key:
            logger.warning("OpenAI API key not provided. Client will operate in offline/stub mode.")
            self.client = None
        else:
            self.client = openai.AsyncOpenAI(api_key=api_key)

    @retry_llm()
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generates a response from an OpenAI model.

        Args:
            messages: A list of messages in the chat format, e.g., [{"role": "user", "content": "Hello"}].
            **kwargs: Additional arguments to pass to the OpenAI API.

        Returns:
            The string content of the assistant's reply.

        Raises:
            BudgetExceededError: If the estimated token usage exceeds the budget.
            openai.APIError: If the API call fails after retries.
        """
        if not self.client:
            logger.info("Simulating OpenAI call (offline mode).")
            # The FixerAgent expects a python markdown block.
            return "```python\ndef my_buggy_function():\n    return 2\n```"

        # Estimate token usage for budget check
        # A more accurate tokenizer would be better, but this is a reasonable proxy.
        estimated_prompt_tokens = sum(len(m.get("content", "")) for m in messages) // 3
        max_completion_tokens = kwargs.get("max_tokens", 1024)
        estimated_total = estimated_prompt_tokens + max_completion_tokens

        if self.budget_meter:
            if not await self.budget_meter.spend(estimated_total):
                raise BudgetExceededError(f"OpenAI call would exceed budget. Estimated tokens: {estimated_total}")

        logger.info("Making OpenAI call to model '%s'...", self.model)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

        return response.choices[0].message.content or ""
