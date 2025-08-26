from __future__ import annotations
import os
import logging
from typing import Dict, Any

from .retry import retry_llm
from .budget_meter import BudgetMeter

logger = logging.getLogger(__name__)

class OpenAIClient:
    """
    A client for interacting with OpenAI's models.

    For the foundational slice, this is a stub that does not make real
    external calls, enforcing the local-only requirement.
    """
    def __init__(self, api_key: str | None = None, budget_meter: BudgetMeter | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.budget_meter = budget_meter

        if not self.api_key:
            logger.warning("OpenAI API key not found. Client will operate in offline mode.")

    @retry_llm()
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generates a response from an OpenAI model.

        In this foundational slice, it returns a hardcoded, successful response
        without making an external API call.
        """
        logger.info(f"Simulating OpenAI call for prompt (first 50 chars): '{prompt[:50]}...'")

        # Simulate token usage for budget meter
        prompt_tokens = len(prompt.split())
        completion_tokens = 50 # A fixed estimate for the stub response

        if self.budget_meter:
            # Simulate a successful spend check
            # In a real scenario, we'd get the cost from config
            self.budget_meter.check_and_spend(
                vendor="openai",
                op_id="stub_op_id",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=0.001
            )

        # Return a hardcoded response that mimics the real API structure
        return {
            "id": "chatcmpl-stub-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a simulated response from the OpenAI stub client.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
