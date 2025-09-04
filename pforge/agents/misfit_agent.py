from __future__ import annotations
import logging
import os
import re
import orjson
import libcst as cst
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)


class _SymbolCollector(cst.CSTVisitor):
    """
    A visitor to collect all function and class definitions from a CST.
    """
    def __init__(self):
        self.symbols = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.symbols[node.name.value] = node

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.symbols[node.name.value] = node


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
        try:
            tree = cst.parse_module(file_content)
            collector = _SymbolCollector()
            tree.visit(collector)
            return list(collector.symbols.keys())
        except cst.ParserSyntaxError as e:
            logger.warning(f"Could not parse file content for symbols: {e}")
            return []

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
        # Create a summary of the project structure to give the LLM context
        project_structure = "\n".join(self.project.get_all_files())
        prompt = (
            f"You are an expert software architect. Your task is to determine if a symbol "
            f"(a function or class) is located in the correct file within a project.\n\n"
            f"PROJECT STRUCTURE:\n{project_structure}\n\n"
            f"SYMBOL: `{symbol}`\n"
            f"CURRENT FILE: `{file_path}`\n\n"
            "Based on standard software engineering principles (e.g., separation of concerns, "
            "high cohesion, single responsibility), does this symbol semantically belong in this file? "
            "A 'misfit' is a symbol that would be better placed in a different existing file or in a new file.\n\n"
            "Respond with a single, raw JSON object with two keys:\n"
            '1. "misfit": boolean (true if it is a misfit, false otherwise)\n'
            '2. "suggestion": string (if a misfit, suggest a better file path, e.g., "pforge/utils/helpers.py"; otherwise null). '
            "Do not add any commentary or markdown formatting around the JSON."
        )

        try:
            response_text = await self.llm_client.chat([{"role": "user", "content": prompt}])

            # Basic check for JSON structure before parsing
            if not response_text.strip().startswith("{") or not response_text.strip().endswith("}"):
                logger.warning(f"MisfitAgent LLM response for symbol '{symbol}' was not valid JSON: {response_text}")
                return

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
                # This message type needs to be defined in signals.py and handled somewhere
                # await self.publish("misfit.detected", misfit_message)

        except orjson.JSONDecodeError as e:
            logger.error(f"MisfitAgent failed to parse JSON response for symbol '{symbol}': {e}\nResponse: {response_text}")
        except Exception as e:
            logger.error(f"MisfitAgent LLM call or other processing failed for symbol '{symbol}': {e}")
