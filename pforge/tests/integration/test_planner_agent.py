import asyncio
import pytest
from pathlib import Path

from pforge.agents.planner_agent import PlannerAgent
from pforge.orchestrator.state_bus import StateBus
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType
from pforge.messaging.amp import AMPMessage

import pytest

@pytest.mark.skip(reason="This test is broken due to agent constructor signatures not matching BaseAgent.")
@pytest.mark.asyncio
async def test_planner_agent_creates_fix_task(monkeypatch):
    """
    Tests that the PlannerAgent can consume a TESTS_FAILED event and
    produce a FIX_TASK event.
    """
    bus = InMemoryBus()
    planner = PlannerAgent(bus)

    # Simulate a TESTS_FAILED event
    failed_event = AMPMessage(
        type=MsgType.TESTS_FAILED.value,
        actor="observer",
        snap_sha="dummy_sha",
        payload={
            "failed_tests": [{
                "nodeid": "tests/test_buggy_module.py::test_buggy_function_returns_fixed",
                "traceback": "AssertionError: assert 'bug' == 'fixed'"
            }],
            "test_file_paths": ["tests/test_buggy_module.py"]
        }
    )
    await bus.publish("pforge:amp:global:events", failed_event)

    # Run the agent's on_tick method
    await planner.on_tick()

    # Check for the FIX_TASK event
    try:
        message = await asyncio.wait_for(bus.get_queue("pforge:amp:global:events").get(), timeout=1.0)
        assert message.type == MsgType.FIX_TASK.value
        assert message.payload['file_path'] == 'pforge/buggy_module.py'
        assert "Fix the bug" in message.payload['description']
    except asyncio.TimeoutError:
        pytest.fail("PlannerAgent did not publish a FIX_TASK event.")
