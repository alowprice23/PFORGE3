from __future__ import annotations
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Set
import orjson
import asyncio
import time

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project


logger = logging.getLogger(__name__)

class FalsePieceAgent(BaseAgent):
    """
    Detects files that are likely dead or unused, proposes their removal,
    and executes the removal upon approval.
    """
    name = "false_piece"
    # This is a heavy operation, run it infrequently.
    detection_interval: float = 60.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.source_root = self.project.root
        self.last_detection_time = 0

        # Subscribe to commands from the Planner
        self.bus.subscribe(self.name, MsgType.ACCEPT_REMOVAL.value)

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
        # This is a simple heuristic. A more advanced approach would use an AST
        # parser or a tool like `vulture`.
        candidates = set()
        all_files = list(self.source_root.rglob("*.py"))

        for file_path in all_files:
            if file_path.name == "__init__.py":
                continue

            module_name = file_path.stem
            try:
                cmd = f"grep -r --exclude='{file_path.name}' '{module_name}' ."
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.source_root)
                if result.returncode == 1 and not result.stdout:
                    candidates.add(file_path)
            except Exception as e:
                logger.error(f"Error running grep for {file_path}: {e}")

        return candidates

    async def on_tick(self):
        """
        On each tick, this agent does two things:
        1. Periodically scans for new false pieces to propose.
        2. Checks for and executes any approved removal tasks.
        """
        # --- 1. Execute approved removals ---
        await self._handle_accepted_removals()

        # --- 2. Periodically detect new false pieces ---
        now = time.time()
        if (now - self.last_detection_time) > self.detection_interval:
            self.last_detection_time = now
            await self._detect_and_propose()

    async def _handle_accepted_removals(self):
        """Processes incoming ACCEPT_REMOVAL commands from the planner."""
        while True:
            try:
                message = await self.bus.get(self.name, timeout=0)
                if not message:
                    break # No more messages

                if message.type != MsgType.ACCEPT_REMOVAL:
                    # This could happen if other messages are sent to this agent
                    continue

                payload = message.payload
                file_path_str = payload.get("file_path")
                op_id = payload.get("op_id")
                token = payload.get("capability_token")

                if not file_path_str or not op_id or not token:
                    logger.error(f"Invalid ACCEPT_REMOVAL message received: {payload}")
                    continue

                logger.info(f"Received ACCEPT_REMOVAL for {file_path_str} with op_id {op_id}")
                self.receive_token(token, op_id)

                # The Planner must grant the capability to delete the file.
                if await self.has_capability("fs:delete", op_id):
                    try:
                        self.project.delete_file(file_path_str)
                        logger.info(f"Successfully deleted false piece: {file_path_str}")

                        # Publish delta signals to notify the EfficiencyAnalyst.
                        fp_delta = Message(type=MsgType.FALSE_PIECE_DELTA, payload={"agent_name": self.name, "value": -1})
                        phi_delta = Message(type=MsgType.PHI_DELTA, payload={"agent_name": self.name, "value": 1})
                        await self.publish(MsgType.FALSE_PIECE_DELTA.value, fp_delta)
                        await self.publish(MsgType.PHI_DELTA.value, phi_delta)
                        logger.info(f"Published FalsePieceDelta and PhiDelta for {file_path_str}")

                    except FileNotFoundError:
                        logger.error(f"Could not delete {file_path_str}: file not found.")
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path_str}: {e}")
                else:
                    logger.error(f"Attempted to delete {file_path_str} without 'fs:delete' capability for op_id {op_id}.")

            except asyncio.QueueEmpty:
                break # No more messages to process

    async def _detect_and_propose(self):
        """Scans for unreferenced files and proposes them for removal."""
        logger.info("FalsePieceAgent scanning for unreferenced files...")
        candidate_files = self._find_unreferenced_files()

        for file_path in candidate_files:
            await self._verify_and_propose(file_path)

    async def _verify_and_propose(self, file_path: Path):
        """Uses an LLM to verify a candidate and proposes it for removal."""
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
                logger.warning(f"False piece detected: {file_path}. Proposing for removal.")

                proposal_message = Message(
                    type=MsgType.PROPOSE_REMOVAL,
                    payload={"file_path": str(file_path.relative_to(self.project.root))}
                )
                await self.publish(MsgType.PROPOSE_REMOVAL.value, proposal_message)

        except Exception as e:
            logger.error(f"FalsePieceAgent LLM call failed for {file_path}: {e}")
