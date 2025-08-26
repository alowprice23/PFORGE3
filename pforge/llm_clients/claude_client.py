from __future__ import annotations
import os
import logging
from typing import Dict, Any, List

from .retry import retry_llm
from .budget_meter import BudgetMeter

logger = logging.getLogger(__name__)

class ClaudeClient:
    """
    A client for interacting with Anthropic's Claude models.

    For the foundational slice, this is a stub that enforces local-only execution.
    """
    def __init__(self, api_key: str | None = None, budget_meter: BudgetMeter | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.budget_meter = budget_meter

        if not self.api_key:
            logger.warning("Anthropic API key not found. Client will operate in offline mode.")

    @retry_llm()
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Generates a response from a Claude model.

        In this foundational slice, it returns a hardcoded, successful response.
        """
        prompt_content = messages[-1].get("content", "")
        logger.info(f"Simulating Claude call for prompt (first 50 chars): '{prompt_content[:50]}...'")

        # Simulate token usage
        prompt_tokens = len(prompt_content.split())
        completion_tokens = 50

        if self.budget_meter:
            self.budget_meter.check_and_spend(
                vendor="anthropic",
                op_id="stub_op_id",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=0.001
            )

        # Return a hardcoded response mimicking the Claude API
        return {
            "id": "msg_stub_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "This is a simulated response from the Claude stub client.",
                }
            ],
            "model": "claude-3-7-sonnet-20240715",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
            },
        }
