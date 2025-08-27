from __future__ import annotations
from typing import Set, List, Optional
import logging

from .dep_graph import DependencyGraph
from .coverage_index import CoverageIndex

logger = logging.getLogger(__name__)

def select_tests(
    changed_files: Set[str],
    dep_graph: DependencyGraph,
    coverage_index: CoverageIndex,
    guard_tests: Optional[Set[str]] = None
) -> List[str]:
    """
    Selects a minimal but sound subset of tests to run based on code changes.

    This is a critical performance optimization that avoids running the entire
    test suite for every small change.

    Args:
        changed_files: A set of source file paths that have changed.
        dep_graph: The project's dependency graph.
        coverage_index: The test-to-file coverage map.
        guard_tests: A set of essential tests that should always be run.

    Returns:
        A sorted list of test nodes (e.g., "tests/test_x.py::test_y") to execute.
    """
    if guard_tests is None:
        guard_tests = set()

    if not changed_files:
        logger.info("No files changed, only running guard tests.")
        return sorted(list(guard_tests))

    # 1. Convert file paths to module names for graph traversal
    # This part assumes a helper function exists to do this mapping.
    # For now, we'll assume the input is already module names.
    changed_modules = changed_files

    # 2. Compute the reverse dependency closure to find all impacted modules
    impacted_modules = dep_graph.get_reverse_closure(changed_modules)
    logger.debug(f"Impacted modules ({len(impacted_modules)}): {impacted_modules}")

    # 3. Find all tests that cover any of the impacted modules
    selected_tests = set()
    for test_node, covered_files in coverage_index.coverage_map.items():
        # Check for intersection between the files covered by the test
        # and the files impacted by the change.
        if not impacted_modules.isdisjoint(covered_files):
            selected_tests.add(test_node)

    logger.info(
        f"Selected {len(selected_tests)} tests based on coverage "
        f"and {len(guard_tests)} guard tests."
    )

    # 4. Add the guard tests and return a unique, sorted list
    final_test_set = selected_tests.union(guard_tests)
    return sorted(list(final_test_set))
