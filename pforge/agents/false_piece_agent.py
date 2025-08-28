from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Set

from .base_agent import BaseAgent
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter

logger = logging.getLogger("agent.falsepiece")
SANDBOX_ROOT = Path(os.getenv("SANDBOX_ROOT", "sandbox_test"))
QUAR_DIR = SANDBOX_ROOT / ".quarantine"

class FalsePieceAgent(BaseAgent):
    name = "false_piece"
    weight = 0.7
    spawn_threshold = 0.08
    retire_threshold = -0.02
    max_tokens_tick = 4_000
    tick_interval = 20.0

    async def on_startup(self) -> None:
        QUAR_DIR.mkdir(exist_ok=True)
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=BudgetMeter(tenant="pforge-dev", daily_quota=1_000_000)
        )
        self.hash_index: Dict[str, Path] = {}
        logger.info("FalsePieceAgent ready")

    async def on_tick(self, state) -> None:
        candidates = self._collect_candidates()
        for f in candidates:
            verdict = await self._ask_o3(f)
            if verdict == "false":
                self._quarantine(f)
                await self.dF(-1)
                await self.dE(-1)
                await self.send_amp(
                    "false_piece_removed",
                    {"file_path": str(f.relative_to(SANDBOX_ROOT))},
                    broadcast=True,
                )
                await self.dH(-0.1)
                await self.dB(+1)

    def _collect_candidates(self) -> Set[Path]:
        unused_files = self._unused_files()
        large_or_tiny = {p for p in SANDBOX_ROOT.rglob("*") if p.is_file() and self._size_outlier(p)}
        duplicates = self._duplicate_files()
        return unused_files | large_or_tiny | duplicates

    def _unused_files(self) -> Set[Path]:
        files = set()
        for file in SANDBOX_ROOT.rglob("*"):
            if not file.is_file():
                continue
            rel = str(file.relative_to(SANDBOX_ROOT))
            try:
                grep = subprocess.run(
                    ["grep", "-R", "-n", rel, "."],
                    cwd=SANDBOX_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if grep.stdout.strip() == "":
                    files.add(file)
            except Exception:
                continue
        return files

    def _size_outlier(self, p: Path) -> bool:
        sz = p.stat().st_size
        return sz < 10 or sz > 1_048_576

    def _duplicate_files(self) -> Set[Path]:
        dupes = set()
        for p in SANDBOX_ROOT.rglob("*"):
            if not p.is_file():
                continue
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            if h in self.hash_index:
                dupes.add(p)
            else:
                self.hash_index[h] = p
        return dupes

    async def _ask_o3(self, f: Path) -> str:
        snippet = f.read_text(encoding="utf-8", errors="ignore").splitlines()[:3]
        prompt = (
            "Repo description: software project under repair.\n"
            f"File path: {f.relative_to(SANDBOX_ROOT)}\n"
            f"First lines:\n{chr(10).join(snippet)}\n\n"
            "Is this file relevant? Reply JSON {\"verdict\": \"false\"|\"true\"}."
        )
        try:
            resp = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=16,
                temperature=0.0,
            )
            data = json.loads(resp)
            return data.get("verdict", "true")
        except Exception as exc:
            logger.debug("o3 false-piece check failed: %s", exc)
            return "true"

    def _quarantine(self, f: Path) -> None:
        target = QUAR_DIR / f.relative_to(SANDBOX_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), target)
        logger.info("Quarantined false piece %s", f)
