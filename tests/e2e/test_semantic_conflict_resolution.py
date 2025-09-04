import pytest
import asyncio
from pathlib import Path
import subprocess
import typer
import toml

from pforge.cli.skills.doctor import run_doctor_flow
from pforge.config import Config, DoctorConfig, LLMConfig, SpecificationsConfig, RecoveryConfig
from pforge.project import Project
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message, MsgType

@pytest.fixture
def mock_config_dict():
    """Provides a default config as a dictionary."""
    return {
        "llm": {"model": "gpt-4-turbo"},
        "doctor": {"retry_limit": 3},
        "specifications": {"raw_config": {}},
        "recovery": {"enabled": False, "checks": []}
    }

@pytest.fixture
def mock_project_with_conflict(tmp_path, mock_config_dict):
    """
    Creates a project with a file that will have conflicting patches.
    """
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    source_file = project_path / "app.py"
    source_file.write_text("def func_a():\n    return 1\n")

    test_file_1 = project_path / "test_app_1.py"
    test_file_1.write_text(
        "from app import func_a\n\ndef test_func_a_1():\n    assert func_a() == 100\n"
    )

    test_file_2 = project_path / "test_app_2.py"
    test_file_2.write_text(
        "from app import func_a\n\ndef test_func_a_2():\n    assert func_a() == 200\n"
    )

    # Create pforge.toml
    config_path = project_path / "pforge.toml"
    with open(config_path, "w") as f:
        toml.dump(mock_config_dict, f)


    # Initialize git repo
    subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=project_path, check=True, capture_output=True)

    return project_path

from pforge.agents.backtracker_agent import BacktrackerAgent
from pforge.agents.conflict_detector_agent import ConflictDetectorAgent

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_semantic_conflict_resolution_e2e(mock_project_with_conflict):
    """
    Tests that a semantic conflict is correctly identified, and a backtrack is triggered.
    """
    project_path = mock_project_with_conflict
    config = Config(
        llm=LLMConfig(model="gpt-4-turbo"),
        doctor=DoctorConfig(retry_limit=3),
        specifications=SpecificationsConfig(raw_config={}),
        recovery=RecoveryConfig(enabled=False, checks=[])
    )
    project = Project(root_path=project_path)
    bus = InMemoryBus()

    # 1. Initialize agents
    conflict_detector = ConflictDetectorAgent(bus, config, project)
    backtracker = BacktrackerAgent(bus, config, project)

    # 2. Subscribe listeners to the final outputs
    bus.subscribe("conflict_listener", MsgType.CONFLICT_ANALYZED.value)
    bus.subscribe("backtrack_listener", MsgType.BACKTRACK_COMPLETED.value)

    # 3. Simulate a workflow where two patches conflict
    file_path = "app.py"
    original_content = "def func_a():\n    return 1"
    project.write_file(file_path, original_content)

    # Patch 1 modifies func_a
    patch_msg_1 = Message(type=MsgType.FIX_PATCH_APPLIED, payload={
        "file_path": file_path, "op_id": "op1", "content": "def func_a():\n    return 100", "original_content": original_content
    })
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, patch_msg_1)

    # Patch 2 also modifies func_a
    patch_msg_2 = Message(type=MsgType.FIX_PATCH_APPLIED, payload={
        "file_path": file_path, "op_id": "op2", "content": "def func_a():\n    return 200", "original_content": original_content
    })
    await bus.publish(MsgType.FIX_PATCH_APPLIED.value, patch_msg_2)

    # 4. Run agents to process the patches
    await conflict_detector.on_tick() # Consumes patch 1
    await conflict_detector.on_tick() # Consumes patch 2

    # 5. Simulate a spec check failure for one of the patches
    spec_failure_msg = Message(
        type=MsgType.SPEC_CHECKED,
        payload={"file_path": file_path, "is_valid": False, "op_id": "op1"}
    )
    await bus.publish(MsgType.SPEC_CHECKED.value, spec_failure_msg)

    # 6. Run agents to process the failure and conflict
    await conflict_detector.on_tick() # Consumes spec failure, finds conflict, publishes CONFLICT_ANALYZED
    await backtracker.on_tick()       # Consumes CONFLICT_ANALYZED, reverts file, publishes BACKTRACK_COMPLETED

    # 7. Assert that the correct messages were published
    conflict_msg = await bus.get("conflict_listener", timeout=1)
    assert conflict_msg is not None
    assert conflict_msg.payload["minimal_hitting_set"] == [file_path]

    backtrack_msg = await bus.get("backtrack_listener", timeout=1)
    assert backtrack_msg is not None
    assert backtrack_msg.payload["file_path"] == file_path
    assert backtrack_msg.payload["status"] == "reverted"
