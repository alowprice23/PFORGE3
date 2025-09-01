from __future__ import annotations
import subprocess
import sys
from pathlib import Path

def install_packages(
    requirements_path: str | Path = "pforge/requirements.txt"
) -> dict:
    """
    Installs package dependencies from a requirements file using pip.

    Args:
        requirements_path: The path to the requirements file.

    Returns:
        A dictionary containing a proof of the action taken.
    """
    try:
        pip_executable = str(Path(sys.executable).parent / "pip")
        command = [pip_executable, "install", "-r", str(requirements_path)]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        proof = {
            "action": "install_packages",
            "status": "success" if process.returncode == 0 else "error",
            "command": " ".join(command),
            "return_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
        return proof
    except Exception as e:
        return {"action": "install_packages", "status": "error", "error": str(e)}
