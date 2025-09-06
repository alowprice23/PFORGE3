from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import tempfile
import os
from typing import Optional

def _run_formatter(command: list[str], path: str | Path, cache_dir: Optional[Path] = None) -> tuple[str, int]:
    """
    A helper function to run a command-line tool and capture its output.
    It redirects to a file to prevent potential deadlocks when a synchronous
    subprocess is called from an async event loop.
    """
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding='utf-8') as f:
        log_path = Path(f.name)

    try:
        executable_dir = Path(sys.executable).parent
        cmd = [str(executable_dir / command[0])] + command[1:] + [str(path)]

        env = os.environ.copy()
        if cache_dir:
            env["RUFF_CACHE_DIR"] = str(cache_dir)

        with log_path.open("w", encoding='utf-8') as f_out:
            process = subprocess.run(
                cmd,
                stdout=f_out,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                env=env,
            )

        output = log_path.read_text(encoding='utf-8')
        return output, process.returncode
    except FileNotFoundError:
        formatter_name = command[0]
        error_msg = f"Error: '{formatter_name}' not found. Is it installed?"
        return error_msg, 1
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        return error_msg, 1
    finally:
        if 'log_path' in locals() and log_path.exists():
            log_path.unlink()


def run_black(path: str | Path) -> tuple[str, int]:
    """
    Runs the black code formatter on a given file or directory.

    Args:
        path: The file or directory path to format.

    Returns:
        A tuple containing the combined stdout and stderr, and the exit code.
    """
    return _run_formatter(["black"], path)


def run_ruff(path: str | Path, fix: bool = True, cache_dir: Optional[Path] = None) -> tuple[str, int]:
    """
    Runs the ruff linter and formatter on a given file or directory.

    Args:
        path: The file or directory path to check.
        fix: If True, runs `ruff format` to automatically fix issues.
             If False, just runs `ruff check`.
        cache_dir: The directory to use for the ruff cache.

    Returns:
        A tuple containing the combined stdout and stderr, and the exit code.
    """
    if fix:
        command = ["ruff", "format"]
    else:
        command = ["ruff", "check"]
    return _run_formatter(command, path, cache_dir)
