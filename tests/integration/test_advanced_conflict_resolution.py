
import pytest

from pforge.agents.backtracker_agent import BacktrackerAgent
from pforge.agents.conflict_detector_agent import ConflictDetectorAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project


@pytest.fixture
def mock_config():
    """Provides a mock config object."""
    class MockConfig:
        def __init__(self):
            self.llm = {"model": "gpt-4-turbo"}
            self.doctor = {"retry_limit": 3}
            self.specifications = {"raw_config": {}}
            self.recovery = {"enabled": False, "checks": []}
            self.budget = {"tenant": "test-tenant", "daily_quota_tokens": 1000}
            self.planner = {"effort_budget_per_tick": 30.0}

    return MockConfig()

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
    Tests that the ConflictDetectorAgent finds a semantic conflict between
    two patches that modify the same function in the same file.
    """
    bus = InMemoryBus()

    # 1. Initialize agents
    conflict_detector = ConflictDetectorAgent(bus, mock_config, mock_project)
    backtracker = BacktrackerAgent(bus, mock_config, mock_project)

    # 2. Subscribe a test listener to the final output of the backtracker
    bus.subscribe("test_listener", MsgType.BACKTRACK_COMPLETED.value)

    # 3. Simulate a workflow
    file_path = "file1.py"
    original_content = "def func_a():\n    return 1\n\ndef func_b():\n    return 2"
    mock_project.write_file(file_path, original_content)

    # Patch 1 modifies func_a
    op_id_1 = "op1"
    content_1 = "def func_a():\n    return 100 # changed\n\ndef func_b():\n    return 2"
    patch_msg_1 = Message(type=MsgType.FIX_PATCH_APPLIED, payload={
        "file_path": file_path, "op_id": op_id_1, "content": content_1, "original_content": original_content
    })
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, patch_msg_1)

    # Patch 2 also modifies func_a
    op_id_2 = "op2"
    content_2 = "def func_a():\n    return 1000 # changed again\n\ndef func_b():\n    return 2"
    patch_msg_2 = Message(type=MsgType.FIX_PATCH_APPLIED, payload={
        "file_path": file_path, "op_id": op_id_2, "content": content_2, "original_content": original_content
    })
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, patch_msg_2)

    # Patch 3 modifies func_b (no conflict)
    op_id_3 = "op3"
    content_3 = "def func_a():\n    return 1\n\ndef func_b():\n    return 200 # changed"
    patch_msg_3 = Message(type=MsgType.FIX_PATCH_APPLIED, payload={
        "file_path": file_path, "op_id": op_id_3, "content": content_3, "original_content": original_content
    })
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, patch_msg_3)


    # Run the conflict detector's tick to process the applied patches
    await conflict_detector.on_tick() # op1
    await conflict_detector.on_tick() # op2
    await conflict_detector.on_tick() # op3

    # A spec check fails for the patch from op_id_1.
    # The conflict detector should find a conflict with op_id_2, but not op_id_3.
    spec_failure_msg = Message(
        type=MsgType.SPEC_CHECKED,
        payload={
            "file_path": file_path,
            "is_valid": False,
            "checks": [{"check": "some_check", "passed": False}],
            "op_id": op_id_1
        }
    )
    await bus.publish(MsgType.SPEC_CHECKED.value, spec_failure_msg)

    # 4. Run the ConflictDetectorAgent to process the spec failure
    await conflict_detector.on_tick()

    # Assert that the correct conflict set was created
    # The key should be the sorted op_ids
    assert "op1:op2" in conflict_detector.conflict_sets
    assert "op1:op3" not in conflict_detector.conflict_sets

    # 5. Run the BacktrackerAgent to process the conflict analysis
    await backtracker.on_tick()

    # 6. Assert that the backtracker reverted the correct file.
    backtrack_msg = await bus.get("test_listener", timeout=1)

    assert backtrack_msg is not None, "BacktrackerAgent did not revert any files."
    assert backtrack_msg.type == MsgType.BACKTRACK_COMPLETED

    reverted_file = backtrack_msg.payload.get("file_path")
    assert reverted_file == file_path
