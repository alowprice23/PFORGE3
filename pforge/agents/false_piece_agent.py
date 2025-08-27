from __future__ import annotations
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Set

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus

logger = logging.getLogger(__name__)

class FalsePieceAgent(BaseAgent):
    """
    Detects files that are likely dead, unused, or extraneous code.
    """
    name = "false_piece"
    tick_interval: float = 30.0  # This is a heavy operation, run it infrequently

    def __init__(self, bus: InMemoryBus, source_root: str | Path = "."):
        super().__init__(bus)
        self.source_root = Path(source_root)

        budget_meter = BudgetMeter(
            tenant="pforge-dev",
            daily_quota_tokens=1_000_000,
            redis_client=self.bus.redis_client
        )
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=budget_meter
        )

    def _find_unreferenced_files(self) -> Set[Path]:
        """Uses grep to find files that are not referenced by any other file."""
        candidates = set()
        all_files = list(self.source_root.rglob("*.py")) # Focus on Python files for now

        for file_path in all_files:
            if file_path.name == "__init__.py":
                continue

            # Grep for the module name (without extension)
            module_name = file_path.stem
            try:
                # Search for the module name in all other files
                cmd = f"grep -r --exclude='{file_path.name}' '{module_name}' ."
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.source_root)
                if result.returncode == 1 and not result.stdout:
                    # Grep returns 1 if no lines are selected
                    candidates.add(file_path)
            except Exception as e:
                logger.error(f"Error running grep for {file_path}: {e}")

        return candidates

    async def on_tick(self):
        logger.info("FalsePieceAgent scanning for unreferenced files...")
        candidate_files = self._find_unreferenced_files()

        for file_path in candidate_files:
            await self._verify_and_report(file_path)

    async def _verify_and_report(self, file_path: Path):
        prompt = (
            f"You are a code maintenance expert. The file '{file_path.relative_to(self.source_root)}' "
            "is not referenced by any other Python file in the project.\n\n"
            "Is this file likely to be dead or unused code that can be safely deleted?\n\n"
            "Respond with a single JSON object with one key:\n"
            '1. "is_false_piece": boolean (true if it is likely dead code, false otherwise)'
        )

        try:
            response_text = await self.llm_client.chat([{"role": "user", "content": prompt}])
            verdict = orjson.loads(response_text)
            if verdict.get("is_false_piece") is True:
                logger.warning(f"False piece detected: {file_path}")

                message = Message(
                    type="false_piece.detected", # New MsgType
                    payload={"file_path": str(file_path)}
                )
                await self.publish("false_piece.detected", message)
        except Exception as e:
            logger.error(f"FalsePieceAgent LLM call failed for {file_path}: {e}")
