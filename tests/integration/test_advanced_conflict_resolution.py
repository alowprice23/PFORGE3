
import pytest

from pforge.agents.backtracker_agent import BacktrackerAgent
from pforge.agents.conflict_detector_agent import ConflictDetectorAgent
from pforge.config import Config, DoctorConfig, LLMConfig, SpecificationsConfig
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project


@pytest.fixture
def mock_config():
    """Provides a default config."""
    return Config(
        llm=LLMConfig(model="gpt-4-turbo"),
        doctor=DoctorConfig(retry_limit=3),
        specifications=SpecificationsConfig(raw_config={})
    )

import subprocess


@pytest.fixture
def mock_project(tmp_path):
    """
    Creates a project with a couple of files and initializes it as a git repo.
    """
    (tmp_path / "file1.py").write_text("initial content 1")
    (tmp_path / "file2.py").write_text("initial content 2")

    # Initialize git repo so backtracker can work
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, check=True, capture_output=True)

    return Project(root_path=tmp_path)

@pytest.mark.asyncio
async def test_advanced_conflict_resolution(mock_config, mock_project):
    """
    Tests that the ConflictDetectorAgent and BacktrackerAgent work together
    to resolve a simple conflict.
    """
    bus = InMemoryBus()

    # 1. Initialize agents
    conflict_detector = ConflictDetectorAgent(bus, mock_config, mock_project)
    backtracker = BacktrackerAgent(bus, mock_config, mock_project)

    # 2. Subscribe a test listener to the final output of the backtracker
    bus.subscribe("test_listener", MsgType.BACKTRACK_COMPLETED.value)

    # 3. Simulate a workflow
    # Two files are "patched" with unique op_ids
    op_id_1 = "op1"
    op_id_2 = "op2"
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, Message(type=MsgType.FIX_PATCH_APPLIED, payload={"file_path": "file1.py", "op_id": op_id_1}))
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, Message(type=MsgType.FIX_PATCH_APPLIED, payload={"file_path": "file2.py", "op_id": op_id_2}))

    # Run the conflict detector's tick to process the applied patches
    await conflict_detector.on_tick() # Processes op1
    await conflict_detector.on_tick() # Processes op2

    # A spec check fails for the patch on file1 (op1).
    # The conflict set should include all active op_ids: {op1, op2}
    spec_failure_msg = Message(
        type=MsgType.SPEC_CHECKED,
        payload={
            "file_path": "file1.py",
            "is_valid": False,
            "checks": [{"check": "some_check", "passed": False}],
            "op_id": op_id_1
        }
    )
    await bus.publish(MsgType.SPEC_CHECKED.value, spec_failure_msg)

    # 4. Run the ConflictDetectorAgent to process the spec failure
    await conflict_detector.on_tick()

    # 5. Run the BacktrackerAgent to process the conflict analysis
    await backtracker.on_tick()

    # 6. Assert that the backtracker reverted at least one file.
    #    In this simple case, the hitting set could be {file1} or {file2}.
    #    We expect at least one backtrack message.
    backtrack_msg = await bus.get("test_listener", timeout=1)

    assert backtrack_msg is not None, "BacktrackerAgent did not revert any files."
    assert backtrack_msg.type == MsgType.BACKTRACK_COMPLETED

    reverted_file = backtrack_msg.payload.get("file_path")
    assert reverted_file in ["file1.py", "file2.py"]
