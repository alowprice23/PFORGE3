from __future__ import annotations
import subprocess
import sys
from pathlib import Path

def _run_formatter(command: list[str], path: str | Path) -> tuple[str, int]:
    """
    A helper function to run a command-line tool and capture its output.

    Args:
        command: The command to run as a list of strings.
        path: The file or directory path to run the formatter on.

    Returns:
        A tuple containing the combined stdout and stderr, and the exit code.
    """
    try:
        # We need to ensure we're using the python from the same environment
        # that is running pforge.
        executable_dir = Path(sys.executable).parent
        cmd = [str(executable_dir / c) for c in command] + [str(path)]

        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Do not raise exception on non-zero exit code
        )
        output = process.stdout + process.stderr
        return output, process.returncode
    except FileNotFoundError:
        # This occurs if the formatter is not installed in the environment.
        formatter_name = command[0]
        return f"Error: '{formatter_name}' not found. Is it installed?", 1
    except Exception as e:
        return f"An unexpected error occurred: {e}", 1


def run_black(path: str | Path) -> tuple[str, int]:
    """
    Runs the black code formatter on a given file or directory.

    Args:
        path: The file or directory path to format.

    Returns:
        A tuple containing the combined stdout and stderr, and the exit code.
    """
    return _run_formatter(["black"], path)


def run_ruff(path: str | Path, fix: bool = True) -> tuple[str, int]:
    """
    Runs the ruff linter and formatter on a given file or directory.

    Args:
        path: The file or directory path to check.
        fix: If True, runs `ruff check --fix` to automatically fix issues.
             If False, just runs `ruff check`.

    Returns:
        A tuple containing the combined stdout and stderr, and the exit code.
    """
    command = ["ruff", "check"]
    if fix:
        command.append("--fix")
    return _run_formatter(command, path)
