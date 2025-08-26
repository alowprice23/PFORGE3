from __future__ import annotations
import subprocess
import orjson
import logging
from pathlib import Path
from typing import Dict, Set

logger = logging.getLogger(__name__)

class CoverageIndex:
    """
    Generates and parses a test-to-file coverage map.

    This index (K) maps each test function to the set of source code files
    it executes, which is essential for targeted test selection.
    """

    def __init__(self, source_root: Path, test_root: Path):
        self.source_root = source_root
        self.test_root = test_root
        # The coverage map: { "test_function_name": {"file1.py", "file2.py"} }
        self.coverage_map: Dict[str, Set[str]] = {}

    def build(self, cov_report_path: Path | str = "coverage.json") -> bool:
        """
        Builds the coverage index by running the test suite with coverage
        and parsing the resulting report.

        Args:
            cov_report_path: The path to save the JSON coverage report to.

        Returns:
            True if the process was successful, False otherwise.
        """
        cov_report_path = Path(cov_report_path)

        # 1. Run pytest with coverage and generate a JSON report.
        # This command assumes pytest and pytest-cov are installed.
        command = [
            "pytest",
            f"--cov={self.source_root}",
            "--cov-report", f"json:{cov_report_path}",
            str(self.test_root)
        ]

        logger.info(f"Building coverage index with command: {' '.join(command)}")

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode not in [0, 1, 5]: # 0=ok, 1=tests failed, 5=no tests collected
            logger.error(f"Coverage run failed with exit code {result.returncode}:\n{result.stderr}")
            return False

        if not cov_report_path.exists():
            logger.error(f"Coverage report file was not created at {cov_report_path}.")
            return False

        # 2. Parse the JSON report to build the map.
        self._parse_report(cov_report_path)

        logger.info(f"Coverage index built successfully with {len(self.coverage_map)} test nodes.")
        return True

    def _parse_report(self, report_path: Path):
        """
        Parses the JSON coverage report into the test-to-file map.

        The format of the JSON report from pytest-cov is:
        {
            "files": {
                "path/to/file.py": { "executed_lines": [...], "contexts": { "test_name": [...] } },
                ...
            }
        }
        """
        self.coverage_map = {}
        report_data = orjson.loads(report_path.read_bytes())

        for file_path, file_data in report_data.get("files", {}).items():
            # The 'contexts' key maps test names to the lines they executed in this file.
            contexts = file_data.get("contexts", {})
            for test_name in contexts.keys():
                # We normalize the test name to be consistent.
                # e.g., "tests/test_api.py::test_endpoint"
                normalized_test_name = test_name.split("|")[0]

                if normalized_test_name not in self.coverage_map:
                    self.coverage_map[normalized_test_name] = set()

                # Add the source file to the set for this test.
                self.coverage_map[normalized_test_name].add(file_path)

    def save(self, index_path: Path | str = "coverage_index.json"):
        """Saves the built coverage map to a file."""
        # Convert sets to lists for JSON serialization.
        serializable_map = {k: list(v) for k, v in self.coverage_map.items()}
        with open(index_path, 'wb') as f:
            f.write(orjson.dumps(serializable_map))

    def load(self, index_path: Path | str = "coverage_index.json"):
        """Loads a pre-built coverage map from a file."""
        with open(index_path, 'rb') as f:
            loaded_map = orjson.loads(f.read())
        # Convert lists back to sets.
        self.coverage_map = {k: set(v) for k, v in loaded_map.items()}
