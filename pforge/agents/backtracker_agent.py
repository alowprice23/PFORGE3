from __future__ import annotations
import json
import logging
import os
import subprocess
from collections import deque
from pathlib import Path
from typing import Deque

from .base_agent import BaseAgent

logger = logging.getLogger("agent.backtracker")
SANDBOX_ROOT = Path(os.getenv("SANDBOX_ROOT", "sandbox_test"))
MAX_CHECKPOINTS = 20

class BacktrackerAgent(BaseAgent):
    name = "backtracker"
    weight = 0.6
    spawn_threshold = 0.05
    retire_threshold = -0.01
    max_tokens_tick = 2_000
    tick_interval = 4.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkpoints: Deque[str] = deque(maxlen=MAX_CHECKPOINTS)

    async def on_startup(self) -> None:
        head = self._current_head()
        if head:
            self.checkpoints.append(head)
        logger.info("Backtracker initial checkpoint %s", head[:7] if head else "none")

    async def on_tick(self, state) -> None:
        rollback_needed, reason = await self._needs_rollback()
        if rollback_needed and len(self.checkpoints) > 0:
            await self._perform_rollback(reason)

        if await self._patch_applied():
            head = self._current_head()
            if head and (not self.checkpoints or head != self.checkpoints[-1]):
                self.checkpoints.append(head)
                logger.debug("Checkpoint stored %s", head[:7])

    async def _needs_rollback(self) -> tuple[bool, str]:
        msgs = await self.read_amp()
        for msg in msgs:
            if msg.get("action") in ("patch_failed", "merge_rejected"):
                return True, msg.get("action")
        return False, ""

    async def _perform_rollback(self, reason: str) -> None:
        target = self.checkpoints[-1]
        subprocess.run(
            ["git", "-C", str(SANDBOX_ROOT), "reset", "--hard", target],
            check=False,
        )
        await self.dB(+1)
        await self.dR(-1)
        await self.send_amp(
            action="rollback_done",
            payload={"commit": target, "reason": reason},
            broadcast=True,
        )
        logger.warning("Rollback to %s due to %s", target[:7], reason)

    async def _patch_applied(self) -> bool:
        msgs = await self.read_amp()
        return any(msg.get("action") == "patch_applied" for msg in msgs)

    def _current_head(self) -> str | None:
        try:
            return subprocess.check_output(
                ["git", "-C", str(SANDBOX_ROOT), "rev-parse", "HEAD"], text=True
            ).strip()
        except subprocess.CalledProcessError:
            return None
