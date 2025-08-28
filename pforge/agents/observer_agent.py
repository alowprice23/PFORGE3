from __future__ import annotations
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Set

import libcst as cst

from pforge.orchestrator.state_bus import PuzzleState
from .base_agent import BaseAgent

SANDBOX_ROOT = Path(os.getenv("SANDBOX_ROOT", "sandbox_test"))

logger = logging.getLogger("agent.observer")

class ObserverAgent(BaseAgent):
    name = "observer"
    weight = 1.0
    spawn_threshold = 0.20
    retire_threshold = -0.10
    max_tokens_tick = 6_000
    tick_interval = 5.0

    _parsed_files: Set[Path] = set()
    _last_git_hash: str | None = None

    async def on_startup(self) -> None:
        logger.info("ObserverAgent starting initial crawl")
        if not SANDBOX_ROOT.exists():
            SANDBOX_ROOT.mkdir(exist_ok=True)
        await self._full_crawl()

    async def on_tick(self, state: PuzzleState) -> None:
        changed = self._sandbox_diff()
        if changed:
            await self._incremental_crawl(changed)

        entropy_score = self._calc_entropy()
        await self.dH(entropy_score - state.entropy)

        if state.tick % 3 == 0:
            await self.send_amp(
                action="file_manifest",
                payload={"files": [str(p.relative_to(SANDBOX_ROOT)) for p in self._parsed_files]},
                broadcast=True,
            )

    async def _full_crawl(self) -> None:
        files = list(SANDBOX_ROOT.rglob("*.*"))
        await self._parse_files(files)
        self._update_git_hash()
        logger.info("ObserverAgent full crawl complete: %d files", len(files))

    async def _incremental_crawl(self, changed: Set[Path]) -> None:
        if not changed:
            return
        await self._parse_files(changed)
        self._update_git_hash()
        logger.debug("ObserverAgent incremental crawl: %d files", len(changed))

    async def _parse_files(self, files) -> None:
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, self._parse_single, f) for f in files]
        await asyncio.gather(*tasks)
        self._parsed_files.update(files)

    def _parse_single(self, file_path: Path) -> None:
        try:
            if file_path.suffix in {".py"}:
                with file_path.open("r", encoding="utf-8") as f:
                    src = f.read()
                module = cst.parse_module(src)
                todo_count = src.count("TODO") + src.count("FIXME")
                if todo_count:
                    asyncio.run(self.dE(todo_count))
        except Exception as exc:
            logger.warning("Parse failed for %s: %s", file_path, exc)

    def _sandbox_diff(self) -> Set[Path]:
        if not (SANDBOX_ROOT / ".git").exists():
            return set()

        new_hash = subprocess.check_output(
            ["git", "-C", str(SANDBOX_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        if self._last_git_hash == new_hash:
            return set()

        if self._last_git_hash is None:
            self._last_git_hash = new_hash
            return set()

        output = subprocess.check_output(
            ["git", "-C", str(SANDBOX_ROOT), "diff", "--name-only", self._last_git_hash, "HEAD"],
            text=True,
        )
        changed = {SANDBOX_ROOT / line.strip() for line in output.splitlines() if line.strip()}
        return changed

    def _update_git_hash(self) -> None:
        if (SANDBOX_ROOT / ".git").exists():
            self._last_git_hash = subprocess.check_output(
                ["git", "-C", str(SANDBOX_ROOT), "rev-parse", "HEAD"], text=True
            ).strip()

    def _calc_entropy(self) -> float:
        todos = sum(
            1
            for p in self._parsed_files
            if p.exists() and "TODO" in p.read_text(encoding="utf-8", errors="ignore")
        )
        if not self._parsed_files:
            return 0.0
        import math

        prob = todos / len(self._parsed_files) if self._parsed_files else 0
        if prob == 0 or prob == 1:
            return 0.0
        return -prob * math.log2(prob) - (1 - prob) * math.log2(1 - prob) if prob > 0 and prob < 1 else 0.0
