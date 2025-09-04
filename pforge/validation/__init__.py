"""
The Validation package provides the machinery for fast, targeted, and
provably sound validation of code changes.

It enables the "fast but honest" philosophy, allowing for rapid progress
by intelligently selecting what to verify, without sacrificing the rigor
required for a final, trustworthy solution.

Modules:
- dep_graph: Builds and queries the module import dependency graph.
- coverage_index: Generates and reads the test-to-file coverage map.
- selection: The targeted test selection algorithm.
- types: The delta typechecking engine.
- test_runner: A secure and robust wrapper for executing tests.
"""

from .dep_graph import DependencyGraph
from .coverage_index import CoverageIndex
from .selection import TestSelector
from .types import run_delta_type_check, TypeCheckResult
from .test_runner import PytestRunner, PytestRunResult

__all__ = [
    "DependencyGraph",
    "CoverageIndex",
    "TestSelector",
    "run_delta_type_check",
    "TypeCheckResult",
    "PytestRunner",
    "PytestRunResult",
]
