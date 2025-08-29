from __future__ import annotations
import os
import logging
from typing import List, Dict, Any

import google.generativeai as genai

from .retry import retry_llm
from .budget_meter import BudgetMeter, BudgetExceededError

logger = logging.getLogger(__name__)

class GeminiClient:
    """A client for interacting with Google's Gemini models, with budget and retry support."""

    def __init__(self, api_key: str | None, model: str = "gemini-1.5-flash", budget_meter: BudgetMeter | None = None):
        self.model_name = model
        self.budget_meter = budget_meter

        if not api_key:
            logger.warning("Gemini API key not provided. Client will operate in offline/stub mode.")
            self.model = None
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)

    @retry_llm()
    async def chat(self, prompt: str, **kwargs) -> str:
        """
        Generates a response from a Gemini model.

        Args:
            prompt: The text prompt to send to the model.
            **kwargs: Additional arguments to pass to the Gemini API.

        Returns:
            The string content of the assistant's reply.

        Raises:
            BudgetExceededError: If the estimated token usage exceeds the budget.
            Exception: If the API call fails after retries.
        """
        if not self.model:
            logger.info("Simulating Gemini call (offline mode).")
            # The PredictorAgent expects a JSON array of suggestions.
            return "[]"

        # Estimate token usage for budget check
        estimated_prompt_tokens = len(prompt) // 3
        max_completion_tokens = kwargs.get("max_output_tokens", 1024)
        estimated_total = estimated_prompt_tokens + max_completion_tokens

        if self.budget_meter:
            if not await self.budget_meter.spend(estimated_total):
                raise BudgetExceededError(f"Gemini call would exceed budget. Estimated tokens: {estimated_total}")

        logger.info("Making Gemini call to model '%s'...", self.model_name)

        response = await self.model.generate_content_async(
            prompt,
            **kwargs
        )

        return response.text or ""
