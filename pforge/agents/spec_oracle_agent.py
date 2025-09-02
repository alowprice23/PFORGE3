from __future__ import annotations
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class SpecOracleAgent(BaseAgent):
    """
    Verifies that changes adhere to the project's configured specifications (Φ).
    This agent acts as a configurable, programmatic oracle for code quality
    and architectural constraints.
    """
    name: str = "spec_oracle"
    tick_interval: float = 1.0

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.source_root = self.project.root
        self.spec_config = self.config.specifications.raw_config
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)
        logger.info(f"Initialized with specification checks: {list(self.spec_config.keys())}")

    async def on_tick(self):
        """
        Checks for FIX_PATCH_APPLIED messages and runs all configured specification checks.
        """
        message = await self.bus.get(self.name, timeout=0.1)
        if not message or message.type != MsgType.FIX_PATCH_APPLIED:
            return

        file_path_str = message.payload.get("file_path")
        if not file_path_str:
            return

        full_path = self.source_root / file_path_str
        if not full_path.exists():
            logger.warning(f"Cannot run spec checks on non-existent file: {full_path}")
            return

        self.logger.info(f"Received FIX_PATCH_APPLIED for {full_path}. Running spec checks.")

        check_results = []
        overall_valid = True

        for check_name, check_config in self.spec_config.items():
            if not check_config.get("enabled", False):
                continue

            if "command" in check_config:
                result = self._run_command_check(check_name, check_config, full_path)
            elif check_name == "disallowed_imports":
                result = self._run_disallowed_imports_check(check_config, full_path)
            else:
                logger.warning(f"Unknown spec check type: {check_name}")
                continue

            check_results.append(result)
            if result.get("passed") is False:
                overall_valid = False

        spec_checked_message = Message(
            type=MsgType.SPEC_CHECKED,
            payload={
                "file_path": file_path_str,
                "is_valid": overall_valid,
                "checks": check_results,
            }
        )
        await self.publish(MsgType.SPEC_CHECKED.value, spec_checked_message)
        self.logger.info(f"Published SPEC_CHECKED for {file_path_str} with overall result: {overall_valid}")

    def _run_command_check(self, name: str, config: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Runs a specification check that is defined as a shell command."""
        command_template = config.get("command")
        if not command_template:
            return {"check": name, "passed": False, "output": "Error: command not defined in config."}

        command = command_template.format(file_path=file_path)
        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.source_root,
                timeout=30
            )
            passed = process.returncode == 0
            output = process.stdout if passed else process.stdout + process.stderr
            return {"check": name, "passed": passed, "output": output.strip()}
        except subprocess.TimeoutExpired:
            return {"check": name, "passed": False, "output": "Error: Command timed out after 30 seconds."}
        except Exception as e:
            return {"check": name, "passed": False, "output": f"Error: Failed to execute command '{command}'. Exception: {e}"}

    def _run_disallowed_imports_check(self, config: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """A custom check to find disallowed import statements."""
        logger.info(f"Running disallowed_imports check on {file_path}")
        rules = config.get("rules", [])
        if not rules:
            return {"check": "disallowed_imports", "passed": True, "output": "No rules configured."}

        try:
            content = file_path.read_text()
            violations = []
            for rule in rules:
                disallowed_import = rule.get("disallow")
                # This is a simple string check. A real implementation would use an AST.
                if f"import {disallowed_import}" in content or f"from {disallowed_import}" in content:
                    violations.append(f"File imports disallowed module '{disallowed_import}'")

            if violations:
                return {"check": "disallowed_imports", "passed": False, "output": "\n".join(violations)}
            else:
                return {"check": "disallowed_imports", "passed": True, "output": "OK"}
        except Exception as e:
            return {"check": "disallowed_imports", "passed": False, "output": f"Error reading file: {e}"}
