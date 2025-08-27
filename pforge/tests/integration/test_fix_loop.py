import asyncio
import unittest
from pathlib import Path
import tempfile
import shutil
import os

from pforge.orchestrator.core import Orchestrator, OrchestratorConfig
from pforge.orchestrator.signals import MsgType, Message
from pforge.validation.test_runner import run_tests

class TestFullAgentLoop(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.test_dir) / "test_project"

        # Create a more realistic project structure
        self.source_dir = self.project_dir / "pforge"
        self.source_dir.mkdir(parents=True)
        (self.source_dir / "__init__.py").touch()

        # Create a buggy file
        (self.source_dir / "buggy_module.py").write_text("def my_buggy_function():\n    return 1\n")

        # Create a failing test for the buggy file
        (self.project_dir / "test_buggy_module.py").write_text(
            "import sys\n"
            "sys.path.insert(0, '.')\n"
            "from pforge.buggy_module import my_buggy_function\n\n"
            "def test_bug():\n"
            "    assert my_buggy_function() == 2\n"
        )

        # Create a spec gap
        self.docs_dir = self.project_dir / "docs"
        self.docs_dir.mkdir()
        (self.docs_dir / "spec.md").write_text("# Specification\n\n- [ ] Implement the 'add' function.\n")


    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_e2e_full_loop(self):
        # Initial test run should fail
        initial_result = run_tests(test_nodes=[], source_root=self.project_dir)
        self.assertIsNotNone(initial_result)
        self.assertEqual(initial_result.failed, 1)

        # Setup orchestrator
        config = OrchestratorConfig.load()
        orchestrator = Orchestrator(config)

        # Instantiate all agents
        from pforge.agents.observer_agent import ObserverAgent
        from pforge.agents.spec_oracle_agent import SpecOracleAgent
        from pforge.agents.predictor_agent import PredictorAgent
        from pforge.agents.planner_agent import PlannerAgent
        from pforge.agents.fixer_agent import FixerAgent

        observer = ObserverAgent(orchestrator.bus, source_root=self.project_dir)
        spec_oracle = SpecOracleAgent(orchestrator.bus, source_root=self.project_dir)
        predictor = PredictorAgent(orchestrator.bus)
        planner = PlannerAgent(orchestrator.bus)
        fixer = FixerAgent(orchestrator.bus, source_root=self.project_dir)

        orchestrator.agents.extend([observer, spec_oracle, predictor, planner, fixer])

        async def run_and_wait_for_events():
            fix_applied_future = asyncio.Future()

            async def listener(message: Message):
                # We just need to see that a patch was applied.
                # A more detailed test could check which bug was fixed.
                if message.type == MsgType.FIX_PATCH_APPLIED:
                    if not fix_applied_future.done():
                        fix_applied_future.set_result(True)

            # Subscribe to the final event in the chain
            orchestrator.bus.subscribe("test_listener", MsgType.FIX_PATCH_APPLIED.value)

            async def consume_for_test():
                while True:
                    msg = await orchestrator.bus.get("test_listener")
                    await listener(msg)

            listener_task = asyncio.create_task(consume_for_test())
            orchestrator_task = asyncio.create_task(orchestrator.run())

            try:
                # Wait for a fix to be applied, with a generous timeout for the full loop
                await asyncio.wait_for(fix_applied_future, timeout=60.0)
            except asyncio.TimeoutError:
                self.fail("Test timed out waiting for a fix to be applied.")
            finally:
                listener_task.cancel()
                orchestrator_task.cancel()
                await asyncio.sleep(0.1)

        asyncio.run(run_and_wait_for_events())

        # At this point, a fix should have been applied.
        # We expect the original test to pass now.
        final_result = run_tests(test_nodes=["test_buggy_module.py"], source_root=self.project_dir)
        self.assertIsNotNone(final_result)
        self.assertEqual(final_result.passed, 1)

if __name__ == '__main__':
    unittest.main()
