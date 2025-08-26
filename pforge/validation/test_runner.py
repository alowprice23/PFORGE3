from __future__ import annotations
import subprocess
import logging
import orjson
from pathlib import Path
from typing import List, NamedTuple, Optional
import uuid

logger = logging.getLogger(__name__)

class TestRunResult(NamedTuple):
    """
    Holds the structured result of a test run.
    """
    exit_code: int
    passed: int
    failed: int
    skipped: int
    duration_s: float
    report_hash: str
    report_content: str
    command: List[str]

def run_tests(
    test_nodes: List[str],
    source_root: Path,
    report_dir: Path = Path("pforge/var/test_reports")
) -> Optional[TestRunResult]:
    """
    Runs a set of specified tests using pytest.

    This function is a secure wrapper that executes pytest, generates a
    structured JSON report, and returns the parsed results.

    Args:
        test_nodes: A list of specific test nodes to run (e.g., "tests/test_x.py").
                    If empty, all tests are run.
        source_root: The root directory to run the tests from.
        report_dir: The directory to store the JSON test report.

    Returns:
        A TestRunResult object, or None if the test run fails catastrophically.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"report-{uuid.uuid4()}.json"

    command = [
        "pytest",
        f"--json-report",
        f"--json-report-file={report_path}",
    ] + test_nodes

    logger.info(f"Running tests with command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=source_root,
            timeout=300 # 5 minute timeout
        )
    except subprocess.TimeoutExpired as e:
        logger.error(f"Test run timed out: {e}")
        return None

    if not report_path.exists():
        logger.error(f"Pytest did not generate a report file at {report_path}.")
        logger.error(f"Stderr: {result.stderr}")
        return None

    # Parse the JSON report
    report_content = report_path.read_bytes()
    report_hash = hashlib.sha256(report_content).hexdigest()
    report_data = orjson.loads(report_content)

    summary = report_data.get("summary", {})

    return TestRunResult(
        exit_code=result.returncode,
        passed=summary.get("passed", 0),
        failed=summary.get("failed", 0),
        skipped=summary.get("skipped", 0),
        duration_s=report_data.get("duration", 0.0),
        report_hash=f"sha256:{report_hash}",
        report_content=report_content.decode('utf-8'),
        command=command
    )
