from __future__ import annotations
import logging
import subprocess
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Set, Optional

logger = logging.getLogger(__name__)

@dataclass
class PytestRunResult:
    """Holds the results of a single test run."""
    exit_code: int
    junit_xml_path: Optional[Path]
    report_hash: Optional[str]
    stdout: str
    stderr: str

    def to_dict(self) -> dict:
        """Converts the dataclass to a dictionary for serialization."""
        # asdict is recursive, but we need to handle Path objects manually.
        d = asdict(self)
        if d.get("junit_xml_path"):
            d["junit_xml_path"] = str(d["junit_xml_path"])
        return d

    def get_counts(self) -> tuple[int, int, int]:
        """Parses the JUnit XML to get passed, failed, and skipped counts."""
        if not self.junit_xml_path or not self.junit_xml_path.exists():
            return 0, 0, 0

        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(self.junit_xml_path)
            root = tree.getroot()
            testsuite = root.find('testsuite')

            failures = int(testsuite.attrib.get('failures', 0))
            skipped = int(testsuite.attrib.get('skipped', 0))
            total = int(testsuite.attrib.get('tests', 0))

            passed = total - failures - skipped
            return passed, failures, skipped
        except (ET.ParseError, KeyError):
            return 0, 0, 0

    @property
    def passed(self) -> bool:
        """True if the test run was successful."""
        # Exit code 0 means tests passed.
        # Exit code 5 means no tests were collected, which is not a failure.
        return self.exit_code in [0, 5]

class PytestRunner:
    """
    A robust wrapper around the test runner (pytest) for executing tests,
    capturing results, and providing verifiable proofs.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.tests_run_since_last_patch: Set[str] = set()

    def run(self, targets: Optional[List[str]] = None, junit_xml_path: str = "test-results.xml", cwd: Optional[str | Path] = None) -> PytestRunResult:
        """
        Runs the test suite or a targeted subset of tests.

        Args:
            targets: An optional list of specific test files or directories to run.
                     If None, the entire test suite is run.
            junit_xml_path: The path to save the JUnit XML report to.
            cwd: The working directory to run the tests in. Defaults to project root.
        """
        working_dir = Path(cwd) if cwd else self.project_root
        junit_full_path = working_dir / junit_xml_path

        import sys
        command = [sys.executable, "-m", "pytest"]
        if targets:
            command.extend(targets)
        else:
            # If no targets, run the default test discovery
            pass

        command.append(f"--junit-xml={junit_full_path}")

        logger.info(f"Running test command: {' '.join(command)} in {working_dir}")

        try:
            env = {"PYTHONPATH": str(working_dir)}
            process = subprocess.run(
                command,
                cwd=working_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=600, # 10-minute timeout
                env=env
            )

            report_hash = None
            if junit_full_path.exists():
                report_content = junit_full_path.read_bytes()
                report_hash = hashlib.sha256(report_content).hexdigest()

                # Update the set of tests run
                if targets:
                    self.tests_run_since_last_patch.update(targets)
                else:
                    # If we ran the full suite, we can mark all known tests as run.
                    # This requires a discovery mechanism, which is out of scope for now.
                    # For now, we'll just use a placeholder.
                    self.tests_run_since_last_patch.add("full_suite")


            return PytestRunResult(
                exit_code=process.returncode,
                junit_xml_path=junit_full_path if junit_full_path.exists() else None,
                report_hash=report_hash,
                stdout=process.stdout,
                stderr=process.stderr
            )

        except subprocess.TimeoutExpired as e:
            logger.error(f"Test run timed out: {e}")
            return TestRunResult(
                exit_code=-1,
                junit_xml_path=None,
                report_hash=None,
                stdout="",
                stderr=f"Timeout: {e}"
            )

    def clear_run_history(self):
        """Clears the history of tests run since the last patch."""
        self.tests_run_since_last_patch.clear()
        logger.info("Cleared test run history.")
