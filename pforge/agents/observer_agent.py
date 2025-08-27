from __future__ import annotations
from pathlib import Path
import time

from .base_agent import BaseAgent
from pforge.validation.dep_graph import DependencyGraph

class ObserverAgent(BaseAgent):
    """
    The primary sensor of the pForge system.

    The ObserverAgent continuously scans the sandbox repository to build an
    "evidence snapshot" of its current state. This includes the dependency
    graph, test coverage, linting issues, and other raw data needed for
    the system's mathematical models.
    """
    name: str = "observer"

    def __init__(self, state_bus, efficiency_engine, source_root: Path | str):
        super().__init__(state_bus, efficiency_engine)
        self.source_root = Path(source_root)
        self.dep_graph = DependencyGraph()

    async def on_startup(self):
        await super().on_startup()
        # In a real run, we would load existing indices if they are not stale.
        self.dep_graph.build_from_path(self.source_root)

    async def on_tick(self):
        """
        On each tick, the ObserverAgent generates a new evidence snapshot
        and publishes it as an OBS.TICK event.
        """
        self.logger.info("Observer tick: generating new evidence snapshot...")

        # For now, we'll use dummy values for the snapshot
        snap_sha = "dummy_snap_sha"

        # 2. Re-build the dependency graph (or check for staleness)
        # For the foundational slice, we'll rebuild it on every tick.
        self.dep_graph.build_from_path(self.source_root)

        # 3. Gather other evidence (placeholders for now)
        lint_issues = [] # Placeholder
        test_outcomes = {} # Placeholder
        entropy_inputs = {} # Placeholder

        # Find the first python file to report as the "problem"
        # This is a simplification for the E2E test.
        target_file = None
        for file in self.source_root.rglob("*.py"):
            target_file = file
            break

        # 4. Assemble the payload for the OBS.TICK event
        payload = {
            "timestamp": time.time(),
            "dependency_graph": self.dep_graph.graph,
            "lint_issues": lint_issues,
            "test_outcomes": test_outcomes,
            "entropy_inputs": entropy_inputs,
            "file_path": str(target_file) if target_file else str(self.source_root),
            "description": "Observed project state."
        }

        # 5. Publish the event
        await self.send_amp_event(
            event_type="OBS.TICK",
            payload=payload,
            snap_sha=snap_sha,
        )

        self.logger.info(f"Published OBS.TICK event for file: {payload.get('file_path')}")
