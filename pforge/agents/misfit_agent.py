from __future__ import annotations
import logging
import os
import re
import orjson
import libcst as cst
from typing import TYPE_CHECKING, Optional
from pydantic import BaseModel, Field, ValidationError

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


class MisfitVerdict(BaseModel):
    misfit: bool = Field(..., description="True if the symbol is a misfit, false otherwise.")
    suggestion: Optional[str] = Field(None, description="If a misfit, a better file path.")


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

        schema = MisfitVerdict.schema_json(indent=2)
        prompt = (
            f"You are an expert software architect. Your task is to determine if a symbol "
            f"(a function or class) is located in the correct file within a project.\n\n"
            f"PROJECT STRUCTURE:\n{project_structure}\n\n"
            f"SYMBOL: `{symbol}`\n"
            f"CURRENT FILE: `{file_path}`\n\n"
            "Based on standard software engineering principles (e.g., separation of concerns, "
            "high cohesion, single responsibility), does this symbol semantically belong in this file? "
            "A 'misfit' is a symbol that would be better placed in a different existing file or in a new file.\n\n"
            "Respond with a single, raw JSON object that conforms to the following JSON Schema:\n"
            f"```json\n{schema}\n```\n"
            "Do not add any commentary or markdown formatting around the JSON."
        )

        try:
            response_text = await self.llm_client.chat([{"role": "user", "content": prompt}])
            verdict = MisfitVerdict.parse_raw(response_text)

            if verdict.misfit:
                logger.warning(f"Misfit detected: '{symbol}' in '{file_path}'. Suggested path: {verdict.suggestion}")

                misfit_message = Message(
                    type=MsgType.MISFIT_DETECTED,
                    payload={
                        "file_path": file_path,
                        "symbol": symbol,
                        "suggestion": verdict.suggestion,
                    }
                )
                await self.publish(misfit_message.type.value, misfit_message)

        except ValidationError as e:
            logger.error(f"MisfitAgent failed to validate Pydantic model for symbol '{symbol}': {e}\nResponse: {response_text}")
        except Exception as e:
            logger.error(f"MisfitAgent LLM call or other processing failed for symbol '{symbol}': {e}")
