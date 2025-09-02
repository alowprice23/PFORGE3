import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from pforge.config import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project

@pytest.mark.asyncio
async def test_misfit_agent_analyzes_rejection_and_publishes(tmp_path):
    """
    Tests that the MisfitAgent correctly handles a FIX_PATCH_REJECTED event.
    1. It should call the LLM to analyze the failure.
    2. It should publish a MISFIT_DETECTED message with the analysis.
    """
    # --- Setup Project and Config ---
    project = Project(tmp_path)
    config = Config.load()

    # --- Setup Orchestrator and Agents ---
    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    misfit_agent = next((a for a in orchestrator.agents if a.name == "misfit"), None)
    assert misfit_agent is not None, "MisfitAgent not found"

    # Mock the LLM client to avoid actual API calls and to control the output
    mock_llm_client = AsyncMock()
    mock_llm_client.chat.return_value = "The patch failed because it returned a string instead of an integer."
    misfit_agent.llm_client = mock_llm_client

    # --- Setup Test Listener ---
    bus = orchestrator.bus
    test_subscriber = "misfit_test_listener"
    bus.subscribe(test_subscriber, MsgType.MISFIT_DETECTED.value)

    # --- Run the Orchestrator ---
    run_task = asyncio.create_task(orchestrator.run())

    # --- Act ---
    # Publish the FIX_PATCH_REJECTED message that the MisfitAgent listens for
    rejected_payload = {
        "file_path": "src/bug.py",
        "patch": "--- a/src/bug.py\n+++ b/src/bug.py\n@@ -1,1 +1,1 @@\n-return 1\n+return 'two'",
        "traceback": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
    }
    rejected_message = Message(
        type=MsgType.FIX_PATCH_REJECTED,
        payload=rejected_payload,
    )
    await bus.publish(MsgType.FIX_PATCH_REJECTED.value, rejected_message)

    # --- Assert ---
    # 1. Check that a MISFIT_DETECTED message was published
    try:
        misfit_message = await bus.get(test_subscriber, timeout=5.0)
        assert misfit_message is not None
        assert misfit_message.type == MsgType.MISFIT_DETECTED

        # The payload should contain the original payload PLUS the analysis
        final_payload = misfit_message.payload
        assert final_payload["file_path"] == "src/bug.py"
        assert final_payload["traceback"] == "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        assert final_payload["misfit_analysis"] == "The patch failed because it returned a string instead of an integer."

    except asyncio.TimeoutError:
        pytest.fail("The MisfitAgent did not publish a MISFIT_DETECTED message in time.")

    # 2. Check that the LLM was called
    mock_llm_client.chat.assert_called_once()
    prompt_arg = mock_llm_client.chat.call_args[0][0][0]['content']
    assert "Here is the patch that was submitted:" in prompt_arg
    assert "Here is the traceback from the test failure:" in prompt_arg
    assert rejected_payload["patch"] in prompt_arg
    assert rejected_payload["traceback"] in prompt_arg


    # --- Cleanup ---
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass
