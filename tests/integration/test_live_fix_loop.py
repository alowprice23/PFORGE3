import asyncio
import subprocess
import tempfile
from pathlib import Path

import orjson
import pytest

from pforge.config import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project
from pforge.validation.test_runner import PytestRunner


@pytest.fixture
def e2e_project():
    """Creates a temporary project with a single bug and a failing test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        (project_dir / "pforge.toml").write_text("[doctor]\nretry_limit = 1\n")

        source_dir = project_dir / "pforge"
        source_dir.mkdir()
        (source_dir / "__init__.py").touch()
        (source_dir / "buggy.py").write_text("def my_buggy_function():\n    return 1\n")

        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").touch()
        (tests_dir / "test_buggy.py").write_text(
            "from pforge.buggy import my_buggy_function\n\n"
            "def test_bug():\n"
            "    assert my_buggy_function() == 2\n"
        )

        # Initialize git for the BacktrackerAgent
        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True, capture_output=True)

        yield project_dir

@pytest.mark.skip(reason="This test requires a live LLM call and an API key.")
@pytest.mark.live
@pytest.mark.asyncio
async def test_live_e2e_full_loop(e2e_project):
    """
    Tests the full end-to-end loop with a real LLM call.
    1. Observer detects a failure.
    2. Planner creates a fix task.
    3. Fixer (LIVE) provides a correct patch.
    4. Observer verifies the fix and confirms tests pass.
    """
    project_dir = e2e_project
    project = Project(project_dir)
    config = Config.load(path=project_dir / "pforge.toml")

    import xml.etree.ElementTree as ET

    # --- Initial state verification ---
    test_runner = PytestRunner(project_root=project_dir)
    initial_result = test_runner.run()
    assert initial_result is not None
    _, failed_count, _ = initial_result.get_counts()
    assert failed_count == 1, "Test should initially fail"

    # --- Setup Orchestrator and listener ---
    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    # We will listen for the final FIX_PATCH_APPLIED signal
    bus = orchestrator.bus
    test_subscriber = "e2e_test_listener"
    bus.subscribe(test_subscriber, MsgType.FIX_PATCH_APPLIED.value)

    # --- Run the Orchestrator ---
    orchestrator_task = asyncio.create_task(orchestrator.run())

    # Manually kick off the process by sending the first TESTS_FAILED message
    # This is faster and more reliable for a test than waiting for the Observer's tick
    # Parse the report to create a realistic payload, mirroring the ObserverAgent's logic
    failed_tests = []
    if initial_result.junit_xml_path:
        tree = ET.parse(initial_result.junit_xml_path)
        root = tree.getroot()
        for testcase in root.iter('testcase'):
            failure = testcase.find('failure')
            if failure is not None:
                failed_tests.append({
                    "nodeid": f"{testcase.attrib.get('classname')}.{testcase.attrib.get('name')}",
                    "traceback": failure.text
                })

    initial_failed_message = Message(
        type=MsgType.TESTS_FAILED,
        payload={"failed_tests": failed_tests}
    )
    await bus.publish(MsgType.TESTS_FAILED.value, initial_failed_message)

    # --- Wait for the outcome ---
    try:
        # Wait for the FIX_PATCH_APPLIED message that signals a successful fix
        final_message = await bus.get(test_subscriber, timeout=60.0) # Increased timeout for live test
        assert final_message is not None
        assert final_message.type == MsgType.FIX_PATCH_APPLIED
    except TimeoutError:
        pytest.fail("Test timed out waiting for a fix to be applied and verified.")
    finally:
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass  # This is expected if the task was still running

    # --- Final state verification ---
    # Verify that the tests now pass
    final_result = test_runner.run()
    assert final_result is not None
    passed_count, failed_count, _ = final_result.get_counts()
    assert passed_count == 1, "Tests should pass after the fix"
    assert failed_count == 0
