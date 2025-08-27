import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from fakeredis import aioredis

from pforge.agents.fixer_agent import FixerAgent
from pforge.orchestrator.state_bus import StateBus
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.proof.bundle import ProofBundle
from pforge.messaging.amp import AMPMessage
from pforge.messaging.redis_stream import stream_add
from pforge.orchestrator.signals import MsgType

@pytest.mark.asyncio
async def test_fixer_agent_receives_task_and_creates_proof():
    """
    Tests that the FixerAgent correctly processes a FIX_TASK, calls the LLM,
    and emits a FIX_PATCH_APPLIED event with a valid ProofBundle.
    """
    # 1. Setup
    redis_client = aioredis.FakeRedis(decode_responses=False) # Match app default
    state_bus = StateBus(redis_client=redis_client)
    efficiency_engine = EfficiencyEngine(constants={})
    amp_stream = "pforge:amp:global:events"

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        buggy_file = project_path / "main.py"
        buggy_file.write_text("def hello():\\n    return 'bug'")

        # 2. Instantiate Agent
        fixer = FixerAgent(state_bus, efficiency_engine)

        # Mock the LLM call to return a predictable patch
        async def mock_generate(*args, **kwargs):
            fixed_content = "def hello():\\n    return 'fix'"
            return {
                "choices": [{"message": {"content": f"```python\\n{fixed_content}\\n```"}}]
            }
        fixer.llm_client.generate = mock_generate

        # 3. Manually send a FIX_TASK message to trigger the fixer
        fix_task_message = AMPMessage(
            type=MsgType.FIX_TASK.value,
            actor="planner_agent", # Pretend to be the planner
            snap_sha="dummy_sha",
            payload={
                "file_path": str(buggy_file),
                "description": "The function returns 'bug' instead of 'fix'."
            }
        )
        await stream_add(redis_client, amp_stream, fix_task_message)
        await asyncio.sleep(0.1) # Give fakeredis a moment to process the write

        # 4. Run Agent's tick manually to process the message
        await fixer.on_tick()

        # 5. Assertions
        messages = await redis_client.xrange(amp_stream)

        assert len(messages) == 2

        patch_applied_event = messages[1]
        msg_data_bytes = patch_applied_event[1]
        amp_message = AMPMessage.from_json(msg_data_bytes[b'amp_json'])

        assert amp_message.type == MsgType.FIX_PATCH_APPLIED.value

        proof_bundle = amp_message.proof
        assert proof_bundle is not None
        assert len(proof_bundle['constraints']) == 1

        obligation = proof_bundle['constraints'][0]
        assert obligation['id'] == "phi.sem.llm_fix"
        assert "The function returns 'bug' instead of 'fix'." in obligation['witness']['prompt']

        payload = amp_message.payload
        assert "return 'fix'" in payload['new_content']
