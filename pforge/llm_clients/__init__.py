"""
The LLM Clients package provides a standardized, robust, and policy-aware
interface for all interactions with external Large Language Models.

It acts as a crucial abstraction layer, isolating the core agent logic
from the implementation details of specific LLM providers.

Modules:
- openai_o3_client: Client for OpenAI models.
- claude_client: Client for Anthropic's Claude models.
- gemini_client: Client for Google's Gemini models.
- retry: A decorator for handling transient API errors with exponential backoff.
- budget_meter: A class for tracking and enforcing token budgets.
- guardrails: (Future) A module for pre-flight safety checks on prompts.
"""

from .openai_o3_client import OpenAIClient
from .claude_client import ClaudeClient
from .gemini_client import GeminiClient
from .retry import retry_llm
from .budget_meter import BudgetMeter, BudgetExceededError

__all__ = [
    "OpenAIClient",
    "ClaudeClient",
    "GeminiClient",
    "retry_llm",
    "BudgetMeter",
    "BudgetExceededError",
]
