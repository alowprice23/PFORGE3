from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import time
import subprocess
import json
import os
import asyncio

from pforge.memory.constellation import Constellation
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.llm_clients.budget_meter import BudgetMeter


@dataclass
class Observation:
    target_path: Path
    tests_exit: Optional[int] = None
    efficiency: Optional[float] = None

    @staticmethod
    def from_env(target_path: Path) -> "Observation":
        # This is a placeholder for a real observation function.
        return Observation(target_path=target_path, tests_exit=0, efficiency=1.0)

class AgenticLoop:
    """The core plan-act-learn loop for the agentic CLI."""

    def __init__(self, memory: Constellation):
        self.memory = memory
        self.actions = [
            ("lint", "ruff ."),
            ("format", "black ."),
            ("test", "pytest"),
        ]
        self.llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=BudgetMeter(tenant="pforge-dev", daily_quota=1_000_000)
        )

    async def process_input(self, user_input: str) -> str:
        prompt = f"""
        You are the pForge agentic CLI. The user said: '{user_input}'.
        Choose the best action from the following list: {', '.join([a[0] for a in self.actions])}.
        Respond with only the name of the action.
        """
        try:
            action_name = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}], max_tokens=50)
            action_name = action_name.strip()

            action = next((a for a in self.actions if a[0] == action_name), None)
            if action:
                rc, out = self._run_command(action[1])
                return f"I ran '{action[0]}'. Exit code: {rc}\nOutput:\n{out}"
            else:
                return f"I don't know how to '{action_name}'."
        except Exception as e:
            return f"An error occurred: {e}"


    def plan_act_learn(self, obs: Observation, budget_steps: int = 8, doctor_mode: bool = False):
        if doctor_mode:
            cmd = "ruff check . --output-format json"
            rc, out = self._run_command(cmd, cwd=obs.target_path)

            if rc != 0 and out:
                try:
                    # Find the start of the JSON array
                    json_start_index = out.find('[')
                    if json_start_index != -1:
                        # Find the end of the JSON array
                        json_end_index = out.rfind(']') + 1
                        json_str = out[json_start_index:json_end_index]
                        issues = json.loads(json_str)
                        for issue in issues:
                            if issue["code"] == "S105":
                                self._fix_hardcoded_password(obs.target_path / issue["filename"])
                                break
                    else:
                        print("No JSON output found from ruff.")
                except json.JSONDecodeError:
                    print("Could not parse ruff output as JSON.")

            # Re-run ruff with --fix to clean up any formatting issues
            cmd_fix = "ruff check --fix ."
            rc_fix, out_fix = self._run_command(cmd_fix, cwd=obs.target_path)
            print("--- RUFF FIX RUN ---")
            print(out_fix)
            print("--- END RUFF FIX RUN ---")

            # Final confirmation run
            cmd_confirm = "ruff check ."
            rc_confirm, out_confirm = self._run_command(cmd_confirm, cwd=obs.target_path)
            print("--- RUFF FINAL CONFIRMATION RUN ---")
            print(out_confirm)
            print("--- END RUFF FINAL CONFIRMATION RUN ---")

    def _fix_hardcoded_password(self, file_path: Path):
        import re
        print(f"Attempting to fix file at absolute path: {file_path.resolve()}")
        content = file_path.read_text()

        if not re.search(r'^import\s+os', content, re.MULTILINE):
            content = "import os\n" + content

        # A more robust regex to find and replace the password assignment
        new_content = re.sub(
            r'(password\s*=\s*)".*"',
            r'\1os.getenv("DB_PASSWORD", "a-secure-default")',
            content
        )

        if new_content != content:
            file_path.write_text(new_content)
            print(f"Fixed hardcoded password in {file_path}")
            print(f"Content of {file_path} is now:\n{file_path.read_text()}")


    def _run_command(self, cmd: str, cwd: Optional[Path] = None) -> tuple[int, str]:
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return process.returncode, process.stdout + process.stderr

    # This is a synchronous wrapper for the async process_input method.
    # It's needed because the chat REPL is synchronous.
    def process_input_sync(self, user_input: str) -> str:
        return asyncio.run(self.process_input(user_input))
