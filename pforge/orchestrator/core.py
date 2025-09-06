from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, TYPE_CHECKING, Any

from pforge.llm_clients.budget_meter import BudgetMeter
from pforge.llm_clients.openai_o3_client import OpenAIClient
from pforge.validation.coverage_index import CoverageIndex
from pforge.validation.dep_graph import DependencyGraph
from pforge.validation.selection import TestSelector
from pforge.validation.test_runner import PytestRunner

if TYPE_CHECKING:
    from pforge.agents.base_agent import BaseAgent
from pforge.config import Config
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.agent_registry import AgentRegistry
from pforge.orchestrator.signals import MsgType, Message
from pforge.orchestrator.state_bus import StateBus
from pforge.project import Project
from pforge.math_models.efficiency import compute_intelligent_efficiency
import os

logger = logging.getLogger("pforge.orchestrator")


class Orchestrator:
    """
    The central coordinator of the pForge system. It registers agents and
    runs their main loops, facilitating communication via an in-memory bus.
    """

    def __init__(self, config: Config, project: Project, puzzle_id: str | None = None):
        self.config = config
        self.project = project
        self.puzzle_id = puzzle_id
        self.bus = InMemoryBus()
        self.state_bus = StateBus(self.bus)
        self.agent_registry = AgentRegistry()
        self.agents: List['BaseAgent'] = []
        self.retry_counts: Dict[str, int] = {}
        self.completion_event = asyncio.Event()
        self.success = False
        self.last_applied_patch = None
        self.dependencies: Dict[str, Any] = {}

        self.bus.subscribe("orchestrator", MsgType.FIX_PATCH_REJECTED.value)
        self.bus.subscribe("orchestrator", MsgType.FIX_PATCH_APPLIED.value)
        self.bus.subscribe("orchestrator", MsgType.SPEC_CHECKED.value)
        self.bus.subscribe("orchestrator", MsgType.CONFLICT_FOUND.value)

    def _create_dependencies(self):
        """Creates and stores shared dependencies for the agents."""
        logger.info("Creating shared dependencies...")

        budget_meter = BudgetMeter(
            tenant=self.config.budget.tenant,
            daily_quota_tokens=self.config.budget.daily_quota_tokens,
            redis_client=self.bus.redis_client
        )
        self.dependencies['budget_meter'] = budget_meter

        llm_client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            budget_meter=budget_meter
        )
        self.dependencies['llm_client'] = llm_client

        dep_graph = DependencyGraph(project_root=self.project.root)
        self.dependencies['dep_graph'] = dep_graph

        coverage_index = CoverageIndex(project_root=self.project.root)
        coverage_index.load()
        self.dependencies['coverage_index'] = coverage_index

        test_selector = TestSelector(dep_graph, coverage_index)
        self.dependencies['test_selector'] = test_selector

        test_runner = PytestRunner(project_root=self.project.root)
        self.dependencies['test_runner'] = test_runner

        logger.info("Shared dependencies created.")


    def setup_agents(self):
        """
        Discovers, creates dependencies, and instantiates all available agents.
        """
        self._create_dependencies()

        for name, agent_class in self.agent_registry.agents.items():

            # This is a simple way to map dependencies. A more robust system
            # might use reflection on the constructor's signature.
            agent_deps = {
                "bus": self.bus,
                "config": self.config,
                "project": self.project,
            }
            if name in ["fixer", "false_piece", "summarizer_agent"]:
                agent_deps["llm_client"] = self.dependencies["llm_client"]
            if name in ["fixer", "false_piece", "observer"]:
                 agent_deps["dep_graph"] = self.dependencies["dep_graph"]
            if name == "fixer":
                agent_deps["coverage_index"] = self.dependencies["coverage_index"]
                agent_deps["test_selector"] = self.dependencies["test_selector"]
                agent_deps["test_runner"] = self.dependencies["test_runner"]


            # Filter agent_class.__init__ signature to pass only required deps
            import inspect
            sig = inspect.signature(agent_class.__init__)
            required_deps = {param: agent_deps[param] for param in sig.parameters if param in agent_deps}

            agent_instance = agent_class(**required_deps)
            self.agents.append(agent_instance)
            logger.info("Instantiated agent: %s", name)

    async def run(self, timeout: float | None = None) -> bool:
        """
        Starts the agent run loops and the message bus.
        Returns True if the puzzle is solved, False otherwise.
        """
        logger.info("Orchestrator starting...")
        if not self.agents:
            logger.warning("No agents registered. Orchestrator will exit.")
            return False

        bus_task = asyncio.create_task(self.bus.start(), name="InMemoryBus")
        orchestrator_loop_task = asyncio.create_task(self._message_loop(), name="OrchestratorLoop")
        agent_tasks = [asyncio.create_task(agent.run_loop()) for agent in self.agents]

        # If a puzzle is defined, kick off the process by simulating a test failure.
        if self.puzzle_id:
            initial_message = Message(
                type=MsgType.TESTS_FAILED,
                payload={"failed_tests": [{"nodeid": self.puzzle_id, "traceback": "Initial puzzle"}]}
            )
            await self.bus.publish(MsgType.TESTS_FAILED.value, initial_message)

        try:
            # Wait for the completion event to be set, with an optional timeout
            await asyncio.wait_for(self.completion_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Orchestrator run timed out.")
            self.success = False
        except asyncio.CancelledError:
            logger.info("Orchestrator run cancelled.")
        finally:
            logger.info("Orchestrator shutting down.")
            for task in agent_tasks:
                task.cancel()
            bus_task.cancel()
            orchestrator_loop_task.cancel()
            await asyncio.gather(
                bus_task, orchestrator_loop_task, *agent_tasks, return_exceptions=True
            )
            logger.info("Orchestrator finished.")

        return self.success

    def stop(self):
        """Stops the orchestrator and all its agents."""
        self.completion_event.set()

    async def _message_loop(self):
        """A loop for the orchestrator to process messages from the bus."""
        while not self.completion_event.is_set():
            try:
                message = await self.bus.get("orchestrator")
                if message:
                    if message.type == MsgType.FIX_PATCH_REJECTED:
                        await self._handle_fix_patch_rejected(message.payload)
                    elif message.type == MsgType.FIX_PATCH_APPLIED:
                        await self._handle_fix_patch_applied(message.payload)
                    elif message.type == MsgType.SPEC_CHECKED:
                        await self._handle_spec_checked(message.payload)
                    elif message.type == MsgType.CONFLICT_FOUND:
                        # For now, the orchestrator just logs this. The BacktrackerAgent will handle it.
                        logger.warning(f"Orchestrator received CONFLICT_FOUND for {message.payload.get('file_path')}")
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in orchestrator message loop: {e}")

    async def _handle_fix_patch_applied(self, payload: Dict):
        """Handles a successful patch, and waits for spec check."""
        file_path = payload.get("file_path")
        logger.info(f"Successfully applied patch to {file_path}. Waiting for spec check...")
        self.last_applied_patch = payload

    async def _handle_spec_checked(self, payload: Dict):
        """Handles a spec check result, declaring the puzzle solved if successful."""
        file_path = payload.get("file_path")
        is_valid = payload.get("is_valid")

        if self.last_applied_patch and self.last_applied_patch.get("file_path") == file_path:
            if is_valid:
                logger.info(f"Spec check passed for {file_path}. Puzzle solved!")
                self.success = True
                self.completion_event.set()
            else:
                logger.warning(f"Spec check failed for {file_path}. The change will be reverted.")
                # The backtracker will handle the revert, but we should reset our state.
                self.last_applied_patch = None


    async def _handle_fix_patch_rejected(self, payload: Dict):
        """Handles a rejected patch, implementing the retry logic."""
        logger.info(f"Handling rejected patch with payload: {payload}")
        file_path = payload.get("file_path")
        if not file_path:
            logger.warning("FIX_PATCH_REJECTED message received without a file_path.")
            return

        current_retry_count = self.retry_counts.get(file_path, 0)
        retry_limit = self.config.doctor.retry_limit

        if current_retry_count < retry_limit:
            self.retry_counts[file_path] = current_retry_count + 1
            logger.info(
                f"Orchestrator logged retry {current_retry_count + 1}/{retry_limit} for bug in {file_path}. "
                "PlannerAgent is responsible for requeueing."
            )
            # The PlannerAgent is subscribed to FIX_PATCH_REJECTED and will handle the retry.
            # The orchestrator's only job is to count and decide when to give up.
        else:
            logger.error(
                f"Could not fix bug in {file_path} after {retry_limit} attempts. Giving up."
            )
            await self.bus.publish(
                MsgType.GIVE_UP.value, Message(type=MsgType.GIVE_UP, payload={"file_path": file_path})
            )
            self.success = False
            self.completion_event.set()

    async def single_tick_update(self):
        """
        Performs a single update of the global puzzle state.
        This can be called periodically or triggered by specific events.
        """
        state = self.state_bus.get_snapshot()
        state.tick += 1

        # In a real system, formula_constants would come from the loaded config
        constants = {} # self.config.formula_constants
        state.efficiency = compute_intelligent_efficiency(state, constants)

        await self.state_bus.publish_update(state)
        logger.debug("Orchestrator tick %d: Efficiency=%.2f", state.tick, state.efficiency)


def main():
    """Example main entry point for running the orchestrator."""
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    config = Config.load()
    project = Project(Path("."))
    orchestrator = Orchestrator(config, project)
    orchestrator.setup_agents()

    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\nOrchestrator shutting down by user request...")


if __name__ == "__main__":
    # This is for demonstration. In the actual app, the CLI or server would instantiate and run the orchestrator.
    main()
