from __future__ import annotations
import logging
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Set, List, Any

logger = logging.getLogger(__name__)

# Default path for the coverage data file and the JSON report
COVERAGE_JSON_PATH = Path("coverage.json")
STALE_THRESHOLD_SECONDS = 3600  # 1 hour

class CoverageIndex:
    """
    Manages the test coverage map. This is a simplified version that only
    knows if a file is covered by any test, not which specific test.
    """

    def __init__(self, project_root: str | Path, coverage_file: str | Path = COVERAGE_JSON_PATH):
        self.project_root = Path(project_root).resolve()
        self.coverage_file = self.project_root / coverage_file
        self.covered_files: Set[str] = set()

    def generate(self, test_path: str = "tests/") -> bool:
        """
        Runs the test suite with coverage enabled to generate a new coverage report.
        """
        logger.info("Generating new coverage report...")

        import sys
        command = [
            sys.executable,
            "-m",
            "pytest",
            "--cov",
            "--cov-report",
            f"json:{self.coverage_file}",
            test_path
        ]

        try:
            env = {"PYTHONPATH": str(self.project_root)}
            process = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
                env=env
            )
            if process.returncode != 0 and process.returncode != 5:
                 logger.error(f"Pytest coverage run failed.\nstdout:\n{process.stdout}\nstderr:\n{process.stderr}")
                 return False

            logger.info("Successfully generated coverage.json file.")
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Coverage generation failed: {e}")
            return False

    def load(self) -> bool:
        """
        Loads the coverage data from the coverage.json file.
        """
        if not self.coverage_file.exists():
            logger.warning("No coverage.json file found. Please generate one first.")
            return False

        logger.info(f"Loading coverage data from {self.coverage_file}...")

        try:
            with open(self.coverage_file, 'r') as f:
                data = json.load(f)

            self.covered_files = set(data.get("files", {}).keys())
            logger.info(f"Coverage map loaded for {len(self.covered_files)} files.")
            return True
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse coverage JSON report: {e}")
            return False

    def is_stale(self, max_age_seconds: int = STALE_THRESHOLD_SECONDS) -> bool:
        """
        Checks if the coverage data is stale based on its modification time.
        """
        if not self.coverage_file.exists():
            return True

        age = time.time() - self.coverage_file.stat().st_mtime
        return age > max_age_seconds

    def is_file_covered(self, file_path: str | Path) -> bool:
        """
        Checks if a file is present in the coverage report.
        """
        str_path = str(file_path.relative_to(self.project_root) if isinstance(file_path, Path) else file_path)
        return str_path in self.covered_files
