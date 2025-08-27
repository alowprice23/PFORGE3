from __future__ import annotations
import subprocess
import logging
import orjson
from pathlib import Path
from typing import List, NamedTuple, Optional
import hashlib
import uuid
import os

logger = logging.getLogger(__name__)

class TestRunnerResult(NamedTuple):
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
    report_dir_name: str = "test_reports"
) -> Optional[TestRunnerResult]:
    """
    Runs a set of specified tests using pytest.
    """
    report_dir = source_root / report_dir_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"report-{uuid.uuid4()}.json"

    command = [
        "python",
        "-m",
        "pytest",
        "--json-report",
        f"--json-report-file={report_path.absolute()}",
    ] + test_nodes

    logger.info(f"Running tests with command: {' '.join(command)}")
    logger.info(f"cwd: {source_root}")

    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=source_root,
            timeout=300, # 5 minute timeout
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        logger.error(f"Test run timed out: {e}")
        return None

    if not report_path.exists():
        logger.error(f"Pytest did not generate a report file at {report_path}.")
        logger.error(f"Stderr: {result.stderr}")
        logger.error(f"Stdout: {result.stdout}")
        return None

    # Parse the JSON report
    report_content = report_path.read_bytes()
    report_hash = hashlib.sha256(report_content).hexdigest()

    try:
        report_data = orjson.loads(report_content)
    except orjson.JSONDecodeError:
        logger.error("Failed to decode test report JSON.")
        logger.error(f"Report content: {report_content.decode('utf-8', errors='ignore')}")
        return None


    summary = report_data.get("summary", {})

    return TestRunnerResult(
        exit_code=result.returncode,
        passed=summary.get("passed", 0),
        failed=summary.get("failed", 0),
        skipped=summary.get("skipped", 0),
        duration_s=report_data.get("duration", 0.0),
        report_hash=f"sha256:{report_hash}",
        report_content=report_content.decode('utf-8'),
        command=command
    )
