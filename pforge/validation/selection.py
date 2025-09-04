from __future__ import annotations
import logging
from pathlib import Path
from typing import List, Set, Optional

from pforge.validation.dep_graph import DependencyGraph
from pforge.validation.coverage_index import CoverageIndex

logger = logging.getLogger(__name__)

# A list of tests that should always be run, regardless of the changes.
GUARD_TESTS = [
    "tests/e2e/doctor_smoke_test.py",
]

class TestSelector:
    """
    Selects a subset of tests to run based on code changes.
    This is a simplified version that runs all tests if any covered file is affected.
    """

    def __init__(self, dep_graph: DependencyGraph, cov_index: CoverageIndex):
        self.dep_graph = dep_graph
        self.cov_index = cov_index
        self.guard_tests = set(GUARD_TESTS)

    def select_tests(self, changed_files: List[str | Path]) -> Optional[List[str]]:
        """
        Selects tests to run. If any changed or dependent file is covered by
        tests, this simplified selector returns None, indicating that the
        entire test suite should be run. Otherwise, it returns only the
        guard tests.

        Args:
            changed_files: A list of file paths that have been modified.

        Returns:
            A list of test nodes to run, or None to run the whole suite.
        """
        if not changed_files:
            return list(self.guard_tests)

        logger.info(f"Selecting tests for changed files: {changed_files}")

        # 1. Compute the reverse dependency closure.
        affected_files: Set[Path] = set()
        for file_path in changed_files:
            p = Path(file_path)
            if not p.is_absolute():
                p = self.dep_graph.project_root / p
            affected_files.add(p)

            reverse_deps = self.dep_graph.get_reverse_dependencies(file_path)
            affected_files.update(reverse_deps)

        logger.info(f"Total affected files (including dependencies): {len(affected_files)}")

        # 2. Check if any affected file is covered.
        for f in affected_files:
            if self.cov_index.is_file_covered(f):
                logger.warning(
                    f"Affected file {f} is covered by tests. "
                    "Running the full test suite as a precaution."
                )
                return None # Signal to run all tests

        # 3. If no affected files are covered, just run the guard tests.
        logger.info("No affected files are covered by tests. Running only guard tests.")
        return list(self.guard_tests)
