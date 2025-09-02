import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import orjson

import pytest

from pforge.config import Config
from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project

@pytest.mark.asyncio
async def test_predictor_agent_predicts_success_and_publishes(tmp_path):
    """
    Tests that the PredictorAgent correctly handles a PROPOSED_PATCH event.
    1. It should call the LLM to predict the success of the patch.
    2. It should publish a PREDICTION_MADE message with the confidence score.
    """
    # --- Setup Project and Config ---
    project = Project(tmp_path)
    config = Config.load()

    # --- Setup Orchestrator and Agents ---
    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    predictor_agent = next((a for a in orchestrator.agents if a.name == "predictor"), None)
    assert predictor_agent is not None, "PredictorAgent not found"

    # Mock the LLM client to avoid actual API calls and to control the output
    mock_llm_client = AsyncMock()
    mock_llm_client.chat.return_value = orjson.dumps({"confidence": 0.95})
    predictor_agent.llm_client = mock_llm_client

    # --- Setup Test Listener ---
    bus = orchestrator.bus
    test_subscriber = "predictor_test_listener"
    bus.subscribe(test_subscriber, MsgType.PREDICTION_MADE.value)

    # --- Run the Orchestrator ---
    run_task = asyncio.create_task(orchestrator.run())

    # --- Act ---
    # Publish the PROPOSED_PATCH message that the PredictorAgent listens for
    proposed_payload = {
        "file_path": "src/bug.py",
        "patch": "--- a/src/bug.py\n+++ b/src/bug.py\n@@ -1,1 +1,1 @@\n-return 1\n+return 2",
        "description": "The bug is that it returns 1 instead of 2",
    }
    proposed_message = Message(
        type=MsgType.PROPOSED_PATCH,
        payload=proposed_payload,
    )
    await bus.publish(MsgType.PROPOSED_PATCH.value, proposed_message)

    # --- Assert ---
    # 1. Check that a PREDICTION_MADE message was published
    try:
        prediction_message = await bus.get(test_subscriber, timeout=5.0)
        assert prediction_message is not None
        assert prediction_message.type == MsgType.PREDICTION_MADE

        # The payload should contain the original payload PLUS the prediction
        final_payload = prediction_message.payload
        assert final_payload["file_path"] == "src/bug.py"
        assert final_payload["description"] == "The bug is that it returns 1 instead of 2"
        assert final_payload["prediction_confidence"] == 0.95

    except asyncio.TimeoutError:
        pytest.fail("The PredictorAgent did not publish a PREDICTION_MADE message in time.")

    # 2. Check that the LLM was called correctly
    mock_llm_client.chat.assert_called_once()
    prompt_arg = mock_llm_client.chat.call_args[0][0][0]['content']
    assert "Your task is to predict the success of a proposed code patch." in prompt_arg
    assert proposed_payload["patch"] in prompt_arg
    assert proposed_payload["description"] in prompt_arg


    # --- Cleanup ---
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass
