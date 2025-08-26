from __future__ import annotations
import os
import logging
from typing import Dict, Any

from .retry import retry_llm
from .budget_meter import BudgetMeter

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    A client for interacting with Google's Gemini models.

    For the foundational slice, this is a stub that enforces local-only execution.
    """
    def __init__(self, api_key: str | None = None, budget_meter: BudgetMeter | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.budget_meter = budget_meter

        if not self.api_key:
            logger.warning("Gemini API key not found. Client will operate in offline mode.")

    @retry_llm()
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generates a response from a Gemini model.

        In this foundational slice, it returns a hardcoded, successful response.
        """
        logger.info(f"Simulating Gemini call for prompt (first 50 chars): '{prompt[:50]}...'")

        # Simulate token usage
        prompt_tokens = len(prompt.split())
        completion_tokens = 50

        if self.budget_meter:
            self.budget_meter.check_and_spend(
                vendor="google",
                op_id="stub_op_id",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=0.001
            )

        # Return a hardcoded response mimicking the Gemini API
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "This is a simulated response from the Gemini stub client."
                            }
                        ],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0,
                }
            ],
            "usageMetadata": {
                "promptTokenCount": prompt_tokens,
                "candidatesTokenCount": completion_tokens,
                "totalTokenCount": prompt_tokens + completion_tokens
            }
        }
