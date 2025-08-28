from __future__ import annotations
import json
import logging
import time
from collections import deque
from typing import Deque, Dict, Optional

from pforge.orchestrator.state_bus import PuzzleState
from .base_agent import BaseAgent

logger = logging.getLogger("agent.planner")

class PlannerAgent(BaseAgent):
    name = "planner"
    weight = 1.2
    spawn_threshold = 0.10
    retire_threshold = -0.05
    max_tokens_tick = 3_000
    tick_interval = 2.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backlog: Deque[Dict] = deque()
        self._ticks_since_prediction: int = 0

    async def on_tick(self, state: PuzzleState) -> None:
        await self._ingest_new_predictions()
        await self._ack_completed_tasks()

        if self.backlog:
            suggestion = self.backlog.popleft()
            await self._dispatch_to_fixer(suggestion)
            self._ticks_since_prediction = 0
        else:
            self._ticks_since_prediction += 1

        if self._ticks_since_prediction > 5 and state.gaps > 0:
            await self.dR(+1)
            self._ticks_since_prediction = 0

    async def _ingest_new_predictions(self) -> None:
        msgs = await self.read_amp()
        for msg in msgs:
            if msg.get("action") == "predictions":
                for sug in msg.get("payload", {}).get("suggestions", []):
                    self._queue_suggestion(sug)

    def _queue_suggestion(self, sug: Dict) -> None:
        entry = {
            "file_path": sug.get("file_path"),
            "stub": sug.get("stub"),
            "confidence": float(sug.get("confidence", 0.5)),
            "ts": time.time(),
        }
        self.backlog.append(entry)
        self.backlog = deque(sorted(self.backlog, key=lambda x: -x["confidence"]))

    async def _dispatch_to_fixer(self, item: Dict) -> None:
        await self.send_amp(
            action="fix_task",
            payload=item,
            metrics={"confidence": item["confidence"]},
        )
        logger.debug("Planner dispatched fix_task for %s", item["file_path"])

    async def _ack_completed_tasks(self) -> None:
        # In a real implementation, we would listen for "patch_applied" messages
        # on a specific topic for the planner agent.
        # For now, we'll just clear the backlog if it gets too big.
        if len(self.backlog) > 100:
            self.backlog.clear()
