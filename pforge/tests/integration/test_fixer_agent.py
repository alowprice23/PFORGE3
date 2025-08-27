import asyncio
import os
import tempfile
import pytest
from pathlib import Path
import subprocess

from pforge.agents.fixer_agent import FixerAgent
from pforge.orchestrator.state_bus import StateBus
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType
from pforge.messaging.amp import AMPMessage
from pforge.llm_clients.openai_o3_client import OpenAIClient

@pytest.mark.asyncio
async def test_fixer_agent_applies_and_verifies_fix(monkeypatch):
    """
    Tests that the FixerAgent can apply a patch and verify it successfully.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create a buggy file and a failing test
        buggy_module_path = project_path / "buggy_module.py"
        buggy_module_path.write_text("def buggy_function():\n    return 'bug'\n")

        tests_dir = project_path / "tests"
        tests_dir.mkdir()
        test_file_path = tests_dir / "test_buggy_module.py"
        test_file_path.write_text(
            "from buggy_module import buggy_function\n"
            "def test_buggy_function_returns_fixed():\n"
            "    assert buggy_function() == 'fixed'\n"
        )

        # Mock the LLM response
        async def mock_generate(*args, **kwargs):
            fixed_content = "def buggy_function():\n    return 'fixed'"
            return {"choices": [{"message": {"content": f"```python\n{fixed_content}\n```"}}]}
        monkeypatch.setattr(OpenAIClient, "generate", mock_generate)

        bus = InMemoryBus()
        state_bus = StateBus(bus=bus)
        efficiency_engine = EfficiencyEngine(constants={})
        fixer = FixerAgent(state_bus, efficiency_engine, source_root=project_path)

        # Simulate a FIX_TASK event
        fix_task = AMPMessage(
            type=MsgType.FIX_TASK.value,
            actor="planner",
            snap_sha="dummy_sha",
            payload={
                "file_path": str(buggy_module_path),
                "description": "Fix the bug in buggy_module.py",
                "failed_test_nodeid": "tests/test_buggy_module.py::test_buggy_function_returns_fixed"
            }
        )
        await bus.publish("pforge:amp:global:events", fix_task)

        # Run the agent's on_tick method
        await fixer.on_tick()

        # Check for the FIX_PATCH_APPLIED event
        try:
            message = await asyncio.wait_for(bus.get_queue("pforge:amp:global:events").get(), timeout=5.0)
            assert message.type == MsgType.FIX_PATCH_APPLIED.value
            assert message.proof.tests['failed'] == 0
            assert message.proof.constraints[0].ok is True
        except asyncio.TimeoutError:
            pytest.fail("FixerAgent did not publish a FIX_PATCH_APPLIED event.")

        # Final check: run pytest on the fixed project
        final_test_result = subprocess.run(
            ["python", "-m", "pytest"], cwd=project_path, capture_output=True, text=True
        )
        assert final_test_result.returncode == 0, f"Test should pass after fix. Stderr: {final_test_result.stderr}"
