from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Type

from pforge.agents.base_agent import BaseAgent
from pforge.config import Config
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.agent_registry import AgentRegistry
from pforge.orchestrator.signals import MsgType, Message
from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.project import Project
from pforge.math_models.efficiency import compute_intelligent_efficiency

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
        self.agents: List[BaseAgent] = []
        self.retry_counts: Dict[str, int] = {}
        self.completion_event = asyncio.Event()
        self.success = False
        self.last_applied_patch = None

        self.bus.subscribe("orchestrator", MsgType.FIX_PATCH_REJECTED.value)
        self.bus.subscribe("orchestrator", MsgType.FIX_PATCH_APPLIED.value)
        self.bus.subscribe("orchestrator", MsgType.SPEC_CHECKED.value)
        self.bus.subscribe("orchestrator", MsgType.CONFLICT_FOUND.value)

    def setup_agents(self):
        """
        Discovers and instantiates all available agents from the registry.
        """
        for name, agent_class in self.agent_registry.agents.items():
            # Pass config and project to each agent
            agent_instance = agent_class(
                bus=self.bus, config=self.config, project=self.project
            )
            self.agents.append(agent_instance)
            logger.info("Instantiated agent: %s", name)

    async def run(self) -> bool:
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
            # Wait for the completion event to be set
            await self.completion_event.wait()
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
        file_path = payload.get("file_path")
        if not file_path:
            logger.warning("FIX_PATCH_REJECTED message received without a file_path.")
            return

        current_retry_count = self.retry_counts.get(file_path, 0)
        retry_limit = self.config.doctor.retry_limit

        if current_retry_count < retry_limit:
            self.retry_counts[file_path] = current_retry_count + 1
            logger.info(
                f"Retry {current_retry_count + 1}/{retry_limit} for bug in {file_path}."
            )
            fix_failed_message = Message(type=MsgType.FIX_FAILED, payload=payload)
            await self.bus.publish(MsgType.FIX_FAILED.value, fix_failed_message)
        else:
            logger.error(
                f"Could not fix bug in {file_path} after {retry_limit} attempts. Giving up."
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
