from __future__ import annotations
import logging
import os
import re
import orjson
from typing import TYPE_CHECKING
from pathlib import Path

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus

logger = logging.getLogger(__name__)

class MisfitAgent(BaseAgent):
    """
    Detects code that is semantically misplaced (e.g., a utility function
    in a data model file).
    """
    name = "misfit"
    tick_interval: float = 2.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)

        budget_meter = BudgetMeter(
            tenant="pforge-dev",
            daily_quota_tokens=1_000_000,
            redis_client=self.bus.redis_client
        )
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=budget_meter
        )

    def _extract_symbols(self, file_content: str) -> list[str]:
        """A simple regex-based parser to find function and class names."""
        # This is a naive implementation; a real one would use an AST parser.
        return re.findall(r"^(?:def|class)\s+([a-zA-Z0-9_]+)", file_content, re.MULTILINE)

    async def on_tick(self):
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.FIX_PATCH_APPLIED:
            return

        file_path_str = message.payload.get("file_path")
        if not file_path_str:
            return

        logger.info(f"MisfitAgent checking for misfits in {file_path_str}")

        try:
            full_path = self.project.root / file_path_str
            if not full_path.exists():
                logger.warning(f"MisfitAgent could not find file to check: {full_path}")
                return
            content = full_path.read_text()
            symbols = self._extract_symbols(content)
        except Exception as e:
            logger.error(f"MisfitAgent could not read or parse {file_path_str}: {e}")
            return

        for symbol in symbols:
            await self._check_symbol_placement(file_path_str, symbol)

    async def _check_symbol_placement(self, file_path: str, symbol: str):
        prompt = (
            f"You are a code architecture reviewer. The function or class '{symbol}' "
            f"is located in the file '{file_path}'.\n\n"
            "Based on standard software engineering principles (e.g., separation of concerns, "
            "high cohesion), does this symbol semantically belong in this file?\n\n"
            "Respond with a single JSON object with two keys:\n"
            '1. "misfit": boolean (true if it is a misfit, false otherwise)\n'
            '2. "suggestion": string (if a misfit, suggest a better file path, e.g., "pforge/utils/helpers.py"; otherwise null)'
        )

        try:
            response_text = await self.llm_client.chat([{"role": "user", "content": prompt}])
            verdict = orjson.loads(response_text)
            if verdict.get("misfit") is True:
                suggestion = verdict.get("suggestion")
                logger.warning(f"Misfit detected: '{symbol}' in '{file_path}'. Suggested path: {suggestion}")

                misfit_message = Message(
                    type="misfit.detected", # New MsgType
                    payload={
                        "file_path": file_path,
                        "symbol": symbol,
                        "suggestion": suggestion,
                    }
                )
                await self.publish("misfit.detected", misfit_message)

        except Exception as e:
            logger.error(f"MisfitAgent LLM call or parsing failed for symbol '{symbol}': {e}")
