from __future__ import annotations
import logging
import os
import re
import orjson
import libcst as cst
from typing import TYPE_CHECKING, Optional
from pydantic import BaseModel, ValidationError

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project
    from pforge.llm_clients.openai_o3_client import OpenAIClient

logger = logging.getLogger(__name__)


class MisfitVerdict(BaseModel):
    """Pydantic model for the LLM's verdict on a symbol's placement."""
    misfit: bool
    suggestion: Optional[str] = None


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

    def __init__(self, bus: InMemoryBus, config: Config, project: Project, llm_client: OpenAIClient):
        super().__init__(bus, config, project)
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)
        self.llm_client = llm_client

    def _extract_symbols(self, file_content: str) -> dict[str, cst.CSTNode]:
        """Extracts function and class definition nodes from file content."""
        try:
            tree = cst.parse_module(file_content)
            collector = _SymbolCollector()
            tree.visit(collector)
            return collector.symbols
        except cst.ParserSyntaxError as e:
            logger.warning(f"Could not parse file content for symbols: {e}")
            return {}

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
            symbols_map = self._extract_symbols(content)
        except Exception as e:
            logger.error(f"MisfitAgent could not read or parse {file_path_str}: {e}")
            return

        for symbol_name, node in symbols_map.items():
            await self._check_symbol_placement(file_path_str, symbol_name, node)

    async def _check_symbol_placement(self, file_path: str, symbol_name: str, node: cst.CSTNode):
        # Create a summary of the project structure to give the LLM context
        project_structure = "\n".join(self.project.list_files())
        symbol_code = cst.Module([node]).code

        system_prompt = (
            "You are an expert software architect AI. Your purpose is to analyze code for "
            "semantic correctness and suggest improvements. You must always respond in the "
            "specified JSON format."
        )
        user_prompt = (
            "Your task is to determine if a symbol (a function or class) is located "
            "in the correct file within a project.\n\n"
            "A 'misfit' is a symbol that would be better placed in a different existing "
            "file or in a new file, based on standard software engineering principles "
            "like separation of concerns, high cohesion, and the single responsibility principle.\n\n"
            "Here is the context:\n\n"
            f"PROJECT STRUCTURE:\n{project_structure}\n\n"
            f"CURRENT FILE: `{file_path}`\n\n"
            f"SYMBOL NAME: `{symbol_name}`\n\n"
            f"SYMBOL SOURCE CODE:\n```\n{symbol_code}\n```\n\n"
            f"Is the symbol `{symbol_name}` a misfit in the file `{file_path}`?\n\n"
            "Respond with a single, raw JSON object with two keys:\n"
            '1. "misfit": boolean (true if it is a misfit, false otherwise).\n'
            '2. "suggestion": string (if it is a misfit, suggest the most appropriate '
            'file path for the symbol, e.g., "pforge/utils/helpers.py"; otherwise, '
            "this should be null).\n\n"
            "Do not add any commentary, explanations, or markdown formatting. "
            "Your entire response must be only the raw JSON object."
        )

        try:
            response_text = await self.llm_client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])

            verdict = MisfitVerdict.parse_raw(response_text)
            if verdict.misfit:
                logger.warning(f"Misfit detected: '{symbol_name}' in '{file_path}'. Suggested path: {verdict.suggestion}")

                misfit_message = Message(
                    type=MsgType.MISFIT_DETECTED,
                    payload={
                        "file_path": file_path,
                        "symbol": symbol_name,
                        "suggestion": verdict.suggestion,
                    }
                )
                await self.publish(MsgType.MISFIT_DETECTED.value, misfit_message)
                logger.info(f"Published MISFIT_DETECTED event for '{symbol_name}' in '{file_path}'")

        except (orjson.JSONDecodeError, ValidationError) as e:
            logger.error(f"MisfitAgent failed to parse JSON response for symbol '{symbol_name}': {e}\nResponse: {response_text}")
        except Exception as e:
            logger.error(f"MisfitAgent LLM call or other processing failed for symbol '{symbol_name}': {e}")
