from __future__ import annotations
import asyncio
import json
import logging
import os
import subprocess
import textwrap
from pathlib import Path
from typing import Dict

from pforge.orchestrator.state_bus import PuzzleState
from .base_agent import BaseAgent
from pforge.llm_clients.claude_client import ClaudeClient
from pforge.llm_clients.budget_meter import BudgetMeter


logger = logging.getLogger("agent.fixer")
SANDBOX_ROOT = Path(os.getenv("SANDBOX_ROOT", "sandbox_test"))

class FixerAgent(BaseAgent):
    name = "fixer"
    weight = 1.4
    spawn_threshold = 0.25
    retire_threshold = 0.02
    max_tokens_tick = 9_000
    tick_interval = 2.0

    async def on_startup(self) -> None:
        # In a real system, the client would be injected or created by a factory
        # based on config. For now, we'll instantiate one directly.
        # The budget meter would also be shared.
        budget_meter = BudgetMeter(
            tenant="pforge-dev",
            daily_quota=1_000_000,
        )
        self.llm_client = ClaudeClient(
            api_key=os.getenv("CLAUDE_API_KEY"),
            budget_meter=budget_meter
        )
        logger.info("FixerAgent ready with Claude 3.7")

    async def on_tick(self, state: PuzzleState) -> None:
        msg = await self._pop_fix_task()
        if not msg:
            return
        success = await self._apply_patch(msg)
        if success:
            await self.dE(-1)
            await self.dM(-1)
        else:
            await self.dB(+1)
            await self.dR(+1)

    async def _pop_fix_task(self) -> Dict | None:
        msgs = await self.read_amp()
        if msgs:
            return msgs[0].get("payload")
        return None

    async def _ask_claude(self, file_path: str, stub: str) -> str | None:
        prompt = textwrap.dedent(
            f"""
            You are FixerAgent. Insert or update the following stub in
            `{file_path}` inside the sandbox repo.  Provide a unified diff.

            Stub to integrate:
            ```python
            {stub}
            ```
            Only respond with the diff, no comments.
            """
        )
        try:
            resp = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.1,
            )
            return resp
        except Exception as exc:
            logger.warning("Claude call failed: %s", exc)
            return None

    async def _apply_patch(self, task: Dict) -> bool:
        file_path, stub = task["file_path"], task["stub"]
        diff = await self._ask_claude(file_path, stub)
        if diff is None:
            return False

        try:
            proc = subprocess.run(
                ["git", "-C", str(SANDBOX_ROOT), "apply", "-"],
                input=diff.encode(),
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            logger.warning("git apply failed: %s", exc.stderr.decode())
            return False

        pass_ok = await self._run_tests(short=True)
        if pass_ok:
            await self._commit_patch(file_path, diff)
            await self.send_amp(
                "patch_applied",
                {"file_path": file_path, "diff": diff},
                broadcast=True,
            )
            logger.info("Patch applied & tests green for %s", file_path)
            return True

        subprocess.run(["git", "-C", str(SANDBOX_ROOT), "reset", "--hard", "HEAD"], check=False)
        await self.send_amp(
            "patch_failed",
            {"file_path": file_path, "reason": "tests_failed"},
            broadcast=True,
        )
        logger.info("Patch reverted due to failing tests for %s", file_path)
        return False

    async def _run_tests(self, short: bool = False) -> bool:
        cmd = ["pytest", "-q"]
        if short:
            cmd += ["-m", "not slow"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=SANDBOX_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _commit_patch(self, file_path: str, diff: str) -> None:
        subprocess.run(["git", "-C", str(SANDBOX_ROOT), "add", "."], check=False)
        subprocess.run(
            ["git", "-C", str(SANDBOX_ROOT), "commit", "-m", f"Fixer patch {file_path}"],
            check=False,
        )
