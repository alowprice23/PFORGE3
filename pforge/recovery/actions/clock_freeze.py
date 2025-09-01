from __future__ import annotations
from pathlib import Path
from pforge.tools.tests_stabilize import inject_clock_fixture

def freeze_clock(file_path: str | Path) -> dict:
    """
    Injects a deterministic 'clock' fixture into the test functions
    within a given file.

    This action uses the `inject_clock_fixture` tool.

    Args:
        file_path: The path to the Python test file to modify.

    Returns:
        A dictionary containing a proof of the action taken.
    """
    try:
        path = Path(file_path)
        original_code = path.read_text()
        modified_code = inject_clock_fixture(original_code)

        if original_code != modified_code:
            path.write_text(modified_code)
            status = "success"
            message = f"Injected clock fixture into {file_path}."
        else:
            status = "no_change"
            message = f"No changes needed for clock fixture in {file_path}."

        proof = {
            "action": "freeze_clock",
            "status": status,
            "file_path": str(file_path),
            "message": message,
        }
        return proof
    except FileNotFoundError:
        return {"action": "freeze_clock", "status": "error", "error": f"File not found: {file_path}"}
    except Exception as e:
        return {"action": "freeze_clock", "status": "error", "error": str(e)}
