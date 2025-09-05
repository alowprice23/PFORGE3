from __future__ import annotations
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Set

from pforge.validation.dep_graph import DependencyGraph

logger = logging.getLogger(__name__)

@dataclass
class TypeCheckResult:
    """Holds the results of a mypy run."""
    exit_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        """True if the type check passed."""
        return self.exit_code == 0

def run_delta_type_check(
    changed_files: List[str | Path],
    dep_graph: DependencyGraph,
    cwd: Optional[str | Path] = None
) -> TypeCheckResult:
    """
    Runs the type checker (mypy) on a minimal set of files affected by changes.

    Args:
        changed_files: A list of file paths that have been modified.
        dep_graph: The project's dependency graph.
        cwd: The working directory to run the type check in. Defaults to project root.

    Returns:
        A TypeCheckResult object with the outcome.
    """
    if not changed_files:
        logger.info("No changed files, skipping type check.")
        return TypeCheckResult(exit_code=0, stdout="No files to check.", stderr="")

    working_dir = Path(cwd) if cwd else dep_graph.project_root

    # 1. Compute the reverse dependency closure to find all affected files.
    affected_files: Set[Path] = set()
    for file_path in changed_files:
        p = Path(file_path)

        # The path of the changed file inside the sandbox
        sandboxed_file = working_dir / p
        affected_files.add(sandboxed_file)

        # The path relative to the project root, for querying the dependency graph
        path_for_graph = p

        reverse_deps = dep_graph.get_reverse_dependencies(path_for_graph)
        # The reverse_deps are absolute paths, we need to make them relative to the sandbox
        for dep in reverse_deps:
            affected_files.add(working_dir / dep.relative_to(dep_graph.project_root))

    logger.info(f"Running type check on {len(affected_files)} affected files in {working_dir}.")

    # 2. Invoke the type checker on this subset of files.
    # The paths passed to mypy should be relative to the cwd.
    command = ["mypy"] + [str(p.relative_to(working_dir)) for p in affected_files]

    try:
        process = subprocess.run(
            command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=300 # 5-minute timeout
        )

        return TypeCheckResult(
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr
        )

    except subprocess.TimeoutExpired as e:
        logger.error(f"Type check timed out: {e}")
        return TypeCheckResult(
            exit_code=-1,
            stdout="",
            stderr=f"Timeout: {e}"
        )
    except FileNotFoundError:
        logger.error("`mypy` command not found. Is it installed and in the system's PATH?")
        return TypeCheckResult(
            exit_code=-1,
            stdout="",
            stderr="`mypy` not found."
        )
