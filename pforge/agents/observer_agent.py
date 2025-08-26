from __future__ import annotations
import logging
from pathlib import Path
import time

from .base_agent import BaseAgent
from pforge.validation.dep_graph import DependencyGraph
from pforge.sandbox.fs_manager import create_snapshot # We need a way to get the current snapshot SHA

class ObserverAgent(BaseAgent):
    """
    The primary sensor of the pForge system.

    The ObserverAgent continuously scans the sandbox repository to build an
    "evidence snapshot" of its current state. This includes the dependency
    graph, test coverage, linting issues, and other raw data needed for
    the system's mathematical models.
    """
    name: str = "observer"

    async def on_startup(self):
        await super().on_startup()
        self.source_root = Path("pforge/workspace") # This should be configured
        self.dep_graph = DependencyGraph()
        # In a real run, we would load existing indices if they are not stale.
        self.dep_graph.build_from_path(self.source_root)

    async def on_tick(self):
        """
        On each tick, the ObserverAgent generates a new evidence snapshot
        and publishes it as an OBS.TICK event.
        """
        self.logger.info("Observer tick: generating new evidence snapshot...")

        # 1. Create a content-addressed snapshot of the current worktree
        # This gives us a stable, verifiable reference to the code state.
        # We need a parent commit; for now, we'll use a placeholder.
        parent_commit = "HEAD" # This would be tracked properly
        commit_sha, snap_sha = create_snapshot(str(self.source_root), parent_commit, "Observer tick snapshot")

        # 2. Re-build the dependency graph (or check for staleness)
        # For the foundational slice, we'll rebuild it on every tick.
        self.dep_graph.build_from_path(self.source_root)

        # 3. Gather other evidence (placeholders for now)
        # In a full implementation, this would involve:
        # - Running linters and static analysis tools.
        # - Getting test outcomes from the test runner.
        # - Calculating raw inputs for the entropy model.
        lint_issues = [] # Placeholder
        test_outcomes = {} # Placeholder
        entropy_inputs = {} # Placeholder

        # 4. Assemble the payload for the OBS.TICK event
        payload = {
            "timestamp": time.time(),
            "dependency_graph": self.dep_graph.graph,
            "lint_issues": lint_issues,
            "test_outcomes": test_outcomes,
            "entropy_inputs": entropy_inputs,
        }

        # 5. Publish the event
        await self.send_amp_event(
            event_type="OBS.TICK",
            payload=payload,
            snap_sha=snap_sha,
        )

        self.logger.info("Published OBS.TICK event.")
