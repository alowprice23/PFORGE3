from __future__ import annotations
import json
import logging
import time
from collections import deque
from typing import Deque, Dict, Optional

from pforge.orchestrator.state_bus import PuzzleState
from pforge.orchestrator.signals import MsgType
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

    async def on_startup(self) -> None:
        self.bus.subscribe(self.name, "amp:global:events")

    async def on_tick(self, state: PuzzleState) -> None:
        await self._process_incoming_messages()

        if self.backlog:
            suggestion = self.backlog.popleft()
            await self._dispatch_to_fixer(suggestion)
            self._ticks_since_prediction = 0
        else:
            self._ticks_since_prediction += 1

        if self._ticks_since_prediction > 5 and state.gaps > 0:
            await self.dR(+1)
            self._ticks_since_prediction = 0

    async def _process_incoming_messages(self) -> None:
        messages = await self.read_amp()
        if messages:
            for msg in messages:
                if msg.type == MsgType.PLAN_PROPOSED:
                    for sug in msg.payload.get("suggestions", []):
                        self._queue_suggestion(sug)
                elif msg.type == MsgType.FIX_PATCH_APPLIED:
                    fp = msg.payload.get("file_path")
                    self.backlog = deque([s for s in self.backlog if s.get("file_path") != fp])
                    await self.dR(-0.5)
                elif msg.type == MsgType.TESTS_FAILED:
                    await self._create_tasks_from_report(msg.payload)

    def _infer_source_from_test(self, test_path: str) -> Optional[str]:
        """
        Infers the source code file path from a test file path.
        Example: `pforge/tests/test_module.py` -> `pforge/module.py`
        """
        if "tests" not in test_path:
            return None

        parts = test_path.split("/")
        if "tests" in parts:
            tests_index = parts.index("tests")
            # a/b/tests/test_c.py -> a/b/c.py
            if parts[-1].startswith("test_"):
                source_filename = parts[-1].replace("test_", "")
                source_path_parts = parts[:tests_index] + [source_filename]
                return "/".join(source_path_parts)
        return None

    async def _create_tasks_from_report(self, payload: Dict) -> None:
        report_content = payload.get("report_content", "{}")
        try:
            report = json.loads(report_content)
            failed_tests = [t for t in report.get("tests", []) if t.get("outcome") == "failed"]

            for test in failed_tests:
                test_node_id = test.get("nodeid", "") # e.g., "pforge/tests/test_buggy.py::test_bug"
                test_filepath = test_node_id.split("::")[0]

                source_filepath = self._infer_source_from_test(test_filepath)
                if source_filepath:
                    suggestion = {
                        "file_path": source_filepath,
                        "stub": f"Fix the bug revealed by test: {test_node_id}",
                        "confidence": 0.75, # Higher confidence for direct test failures
                    }
                    self._queue_suggestion(suggestion)
                    await self.dR(+0.2) # Increment desire for a fix
                else:
                    logger.warning("Could not infer source for failed test: %s", test_filepath)

        except json.JSONDecodeError:
            logger.error("Failed to decode test report JSON.")

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

