from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from typing import Tuple
from packaging.version import parse as parse_version

def check_tool_version(
    tool_name: str, expected_version_spec: str
) -> Tuple[bool, dict]:
    """
    Checks that the version of a development tool meets a specifier.

    Args:
        tool_name: The name of the command-line tool (e.g., 'mypy', 'pytest').
        expected_version_spec: A PEP 440 version specifier (e.g., '==1.10.0', '>=8.2').

    Returns:
        A tuple containing a boolean indicating if the check passed, and a
        details dictionary.
    """
    try:
        # Ensure we're using the tool from the correct environment.
        executable_path = Path(sys.executable).parent / tool_name
        command = [str(executable_path), "--version"]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        output = process.stdout.strip()

        # A simple regex to find version-like strings.
        import re
        match = re.search(r"(\d+\.\d+(\.\d+)?)", output)
        if not match:
            return False, {"status": "error", "error": "Could not parse version from output."}

        actual_version = parse_version(match.group(1))

        # Use packaging library to check against the specifier
        from packaging.specifiers import SpecifierSet
        spec = SpecifierSet(expected_version_spec)
        is_ok = actual_version in spec

        witness = {
            "tool": tool_name,
            "expected_spec": expected_version_spec,
            "actual_version": str(actual_version),
            "version_output": output,
        }
        return is_ok, witness

    except FileNotFoundError:
        return False, {"status": "error", "error": f"Tool not found: {tool_name}"}
    except subprocess.CalledProcessError as e:
        return False, {"status": "error", "error": f"Command failed: {e.stderr}"}
    except Exception as e:
        return False, {"status": "error", "error": str(e)}
