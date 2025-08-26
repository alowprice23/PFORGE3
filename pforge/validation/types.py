from __future__ import annotations
import subprocess
import logging
from pathlib import Path
from typing import Set, List, NamedTuple

from .dep_graph import DependencyGraph

logger = logging.getLogger(__name__)

class TypeCheckResult(NamedTuple):
    """
    Holds the result of a type checking operation.
    """
    exit_code: int
    report: str
    files_checked: List[str]

def run_delta_typecheck(
    changed_files: Set[str],
    dep_graph: DependencyGraph,
    source_root: Path
) -> TypeCheckResult:
    """
    Runs the typechecker on a minimal subset of files affected by a change.

    This avoids the overhead of type-checking the entire codebase for small,
    localized changes.

    Args:
        changed_files: A set of source file paths that have changed.
        dep_graph: The project's dependency graph.
        source_root: The root path of the source code to check.

    Returns:
        A TypeCheckResult object with the outcome.
    """
    # 1. Determine the full set of files to check
    # This includes the changed files plus any files that depend on them.
    # We assume file paths are relative to the source_root for the graph.
    changed_modules = {str(p.relative_to(source_root)) for p in changed_files}
    impacted_modules = dep_graph.get_reverse_closure(changed_modules)

    files_to_check = [str(source_root / m.replace('.', '/')) + '.py' for m in impacted_modules]

    if not files_to_check:
        logger.info("No files to type check.")
        return TypeCheckResult(exit_code=0, report="", files_checked=[])

    # 2. Invoke the typechecker (mypy)
    # We use mypy here, but this could be configured to use pyright, etc.
    command = [
        "mypy",
        "--ignore-missing-imports",
        "--follow-imports=silent",
        "--show-error-codes",
    ] + files_to_check

    logger.info(f"Running delta type check on {len(files_to_check)} files...")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=source_root
    )

    return TypeCheckResult(
        exit_code=result.returncode,
        report=result.stdout,
        files_checked=files_to_check,
    )
