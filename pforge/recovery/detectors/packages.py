from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from typing import Tuple

def _run_command(command: list[str], cwd: str | Path | None = None) -> Tuple[bool, dict]:
    """Helper to run a command and return a standardized result."""
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        is_ok = process.returncode == 0
        witness = {
            "command": " ".join(command),
            "return_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
        return is_ok, witness
    except FileNotFoundError:
        return False, {"error": f"Command not found: {command[0]}"}
    except Exception as e:
        return False, {"error": str(e)}


def check_pip_dependencies() -> Tuple[bool, dict]:
    """
    Runs `pip check` to verify the integrity of Python package dependencies.
    """
    # Ensure we're using the pip from the correct environment.
    pip_executable = str(Path(sys.executable).parent / "pip")
    return _run_command([pip_executable, "check"])


def check_npm_dependencies(repo_root: str | Path) -> Tuple[bool, dict]:
    """
    Runs `npm ci --dry-run` to verify the integrity of Node.js package dependencies.

    This check assumes `package.json` and `package-lock.json` are in the
    provided repo_root.
    """
    if not (Path(repo_root) / "package.json").exists():
        return True, {"skipped": "No package.json found."}

    return _run_command(["npm", "ci", "--dry-run"], cwd=repo_root)
