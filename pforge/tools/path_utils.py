from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pforge.project import Project

logger = logging.getLogger(__name__)

def infer_source_path_from_test_nodeid(nodeid: str, project: Project) -> str | None:
    """
    Infers a source file from a test file path using a heuristic and checks
    for its existence in the project.
    """
    if not nodeid:
        return None

    test_file_path = nodeid.split("::")[0]

    # This logic is still a simple heuristic
    if "tests/unit/" in test_file_path:
        base_name = test_file_path.replace("tests/unit/test_", "")
    elif "tests/integration/" in test_file_path:
        base_name = test_file_path.replace("tests/integration/test_", "")
    else:
        # Handle cases where test is not in a conventional subdir (e.g., tests/test_buggy.py)
        base_name = test_file_path.replace("tests/", "").replace("test_", "")

    # Now, try to find this file in the project
    # This assumes a conventional project structure (e.g., code in 'pforge/' or 'src/')
    potential_paths = [
        Path("pforge") / base_name,
        Path("src") / base_name,
        Path(base_name)
    ]

    for rel_path in potential_paths:
        # Use project.root which is the root of the target project
        if (project.root / rel_path).exists():
            return str(rel_path.as_posix())

    logger.warning(f"Could not find a matching source file for test path: {test_file_path}")
    return None
