import asyncio
from unittest.mock import patch, MagicMock

import pytest

from pforge.config import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project

@pytest.mark.asyncio
async def test_backtracker_agent_reverts_and_rejects_on_failure(tmp_path):
    """
    Tests that the BacktrackerAgent correctly handles a VERIFICATION_FAILED event.
    1. It should call the patch_manager's revert_last_patch method.
    2. It should publish a FIX_PATCH_REJECTED message to trigger a retry.
    """
    # --- Setup Project and Config ---
    project = Project(tmp_path)
    config = Config.load() # Load default config

    # --- Setup Orchestrator and Agents ---
    # The orchestrator will automatically discover and instantiate the BacktrackerAgent
    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    # Find the backtracker agent to mock its patch_manager
    backtracker_agent = next((a for a in orchestrator.agents if a.name == "backtracker"), None)
    assert backtracker_agent is not None, "BacktrackerAgent not found"

    # Mock the patch manager to avoid actual git operations
    mock_patch_manager = MagicMock()
    mock_patch_manager.revert_last_patch.return_value = True
    backtracker_agent.patch_manager = mock_patch_manager

    # --- Setup Test Listener ---
    bus = orchestrator.bus
    test_subscriber = "backtracker_test_listener"
    bus.subscribe(test_subscriber, MsgType.FIX_PATCH_REJECTED.value)

    # --- Run the Orchestrator ---
    # We don't need the full orchestrator loop, just the bus and agents
    run_task = asyncio.create_task(orchestrator.run())

    # --- Act ---
    # Publish the VERIFICATION_FAILED message that the BacktrackerAgent listens for
    original_payload = {
        "file_path": "src/bug.py",
        "patch": "--- a/src/bug.py\n+++ b/src/bug.py\n@@ -1,1 +1,1 @@\n-return 1\n+return 2",
        "description": "The bug is that it returns 1 instead of 2",
    }
    verification_failed_message = Message(
        type=MsgType.VERIFICATION_FAILED,
        payload=original_payload,
    )
    await bus.publish(MsgType.VERIFICATION_FAILED.value, verification_failed_message)

    # --- Assert ---
    # 1. Check that a FIX_PATCH_REJECTED message was published
    try:
        rejected_message = await bus.get(test_subscriber, timeout=5.0)
        assert rejected_message is not None
        assert rejected_message.type == MsgType.FIX_PATCH_REJECTED
        # The payload should be the same as the original payload that failed
        assert rejected_message.payload == original_payload
    except asyncio.TimeoutError:
        pytest.fail("The BacktrackerAgent did not publish a FIX_PATCH_REJECTED message in time.")

    # 2. Check that the patch manager's revert method was called
    mock_patch_manager.revert_last_patch.assert_called_once()

    # --- Cleanup ---
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_backtracker_agent_reverts_file_on_conflict(tmp_path):
    """
    Tests that the BacktrackerAgent correctly handles a CONFLICT_FOUND event.
    It should call the patch_manager's revert_file method with the correct file path.
    """
    # --- Setup Project and Config ---
    project = Project(tmp_path)
    config = Config.load() # Load default config

    # --- Setup Orchestrator and Agents ---
    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    backtracker_agent = next((a for a in orchestrator.agents if a.name == "backtracker"), None)
    assert backtracker_agent is not None, "BacktrackerAgent not found"

    # Mock the patch manager to avoid actual git operations
    mock_patch_manager = MagicMock()
    backtracker_agent.patch_manager = mock_patch_manager

    # --- Run the Orchestrator ---
    run_task = asyncio.create_task(orchestrator.run())

    # --- Act ---
    # Publish the CONFLICT_FOUND message
    conflict_payload = {"file_path": "src/merge_conflict.py"}
    conflict_message = Message(
        type=MsgType.CONFLICT_FOUND,
        payload=conflict_payload,
    )
    await orchestrator.bus.publish(MsgType.CONFLICT_FOUND.value, conflict_message)

    # Give the agent a moment to process the message
    await asyncio.sleep(1.0)

    # --- Assert ---
    # Check that the patch manager's revert_file method was called with the correct path
    mock_patch_manager.revert_file.assert_called_once_with("src/merge_conflict.py")

    # --- Cleanup ---
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass
