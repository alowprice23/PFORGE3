from __future__ import annotations
import os
import logging
from typing import Dict, Any

import openai
from dotenv import load_dotenv

from .retry import retry_llm
from .budget_meter import BudgetMeter

logger = logging.getLogger(__name__)

class OpenAIClient:
    """
    A client for interacting with OpenAI's models.
    """
    def __init__(self, budget_meter: BudgetMeter | None = None):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "dummy_openai_key":
            logger.warning("OpenAI API key not found or is a dummy key. Client will operate in offline mode.")
            self.client = None
        else:
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        self.budget_meter = budget_meter


    @retry_llm()
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generates a response from an OpenAI model.
        """
        if not self.client:
            logger.info(f"Simulating OpenAI call for prompt (first 50 chars): '{prompt[:50]}...'")
            # Return a hardcoded response if the client is not initialized
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
                    "prompt_tokens": 50,
                    "completion_tokens": 50,
                    "total_tokens": 100,
                },
            }

        logger.info(f"Making OpenAI call for prompt (first 50 chars): '{prompt[:50]}...'")

        if self.budget_meter:
            # We can do a pre-check here if we want.
            # For now, we will check and spend after the call.
            pass

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )

        completion_tokens = response.usage.completion_tokens
        prompt_tokens_from_api = response.usage.prompt_tokens

        if self.budget_meter:
            # In a real scenario, we'd get the cost from config
            cost_usd = 0.001
            self.budget_meter.check_and_spend(
                vendor="openai",
                op_id="op_id_from_context", # This should be passed in
                prompt_tokens=prompt_tokens_from_api,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd
            )

        return response.model_dump()
