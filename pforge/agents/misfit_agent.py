from __future__ import annotations
import logging
import os
import re
import json
from typing import List, Tuple
import asyncio
from pathlib import Path

from .base_agent import BaseAgent
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter
import textwrap

logger = logging.getLogger("agent.misfit")
SANDBOX_ROOT = Path(os.getenv("SANDBOX_ROOT", "sandbox_test"))

class MisfitAgent(BaseAgent):
    name = "misfit"
    weight = 1.1
    spawn_threshold = 0.12
    retire_threshold = -0.03
    max_tokens_tick = 5_000
    tick_interval = 6.0

    async def on_startup(self) -> None:
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=BudgetMeter(tenant="pforge-dev", daily_quota=1_000_000)
        )
        self._no_misfit_ticks: int = 0
        logger.info("MisfitAgent ready with OpenAI o3")

    async def on_tick(self, state) -> None:
        symbols = self._recent_symbols()
        if not symbols:
            self._no_misfit_ticks += 1
            if self._no_misfit_ticks >= 3 and state.misfits > 0:
                await self.dM(-1)
                self._no_misfit_ticks = 0
            return

        for file_path, symbol in symbols:
            verdict, suggestion = await self._ask_o3(file_path, symbol)
            if verdict == "misfit":
                await self._report_misfit(file_path, symbol, suggestion)
                await self.dM(+1)
                self._no_misfit_ticks = 0

    def _recent_symbols(self) -> List[Tuple[str, str]]:
        # This is a placeholder for a real implementation that would get
        # the recently changed symbols from the orchestrator or another agent.
        return []

    async def _ask_o3(self, file_path: str, symbol: str) -> Tuple[str, str]:
        prompt = textwrap.dedent(
            f"""
            You are a code reviewer. The symbol `{symbol}` was added to file
            `{file_path}`. Based on typical project organisation
            (helpers in utils/, business logic in services/, data in models/),
            decide if this symbol is misplaced.

            Respond strictly as JSON:
            {{ "verdict": "fit"|"misfit", "suggested_path": "<path>|null" }}
            """
        )
        try:
            resp = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=64,
                temperature=0.0,
            )
            data = json.loads(resp)
            return data.get("verdict", "fit"), data.get("suggested_path") or file_path
        except Exception as exc:
            logger.debug("o3 misfit check failed: %s", exc)
            return "fit", file_path

    async def _report_misfit(self, file_path: str, symbol: str, suggestion: str) -> None:
        await self.send_amp(
            action="misfit_report",
            payload={
                "file_path": file_path,
                "symbol": symbol,
                "suggested_path": suggestion,
            },
            broadcast=True,
        )
        logger.info("Misfit detected: %s.%s -> suggest %s", file_path, symbol, suggestion)
