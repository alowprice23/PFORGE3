from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.validation.coverage_index import CoverageIndex

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

class SelfRepairAgent(BaseAgent):
    """
    An agent responsible for maintaining the health and integrity of the
    pForge system itself. For example, it ensures that cached data like
    the coverage index is not stale.
    """
    name = "self_repair"
    tick_interval: float = 300.0  # Check every 5 minutes

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.coverage_index = CoverageIndex(project_root=self.project.root)

        # Load the index on startup if it exists and is not stale.
        if not self.coverage_index.is_stale():
            self.coverage_index.load()
        else:
            logger.warning("Coverage index is stale or missing on startup. It will be rebuilt on the next tick.")

    async def on_tick(self):
        """
        Periodically checks for system health issues and triggers repairs.
        """
        logger.info("SelfRepairAgent performing health checks...")
        await self._check_and_repair_coverage_index()

    async def _check_and_repair_coverage_index(self):
        """
        Checks if the coverage index is stale and regenerates it if needed.
        """
        if self.coverage_index.is_stale():
            logger.warning("Coverage index is stale. Triggering regeneration.")

            success_generate = self.coverage_index.generate()

            if success_generate:
                logger.info("Successfully regenerated coverage data. Loading new index.")
                success_load = self.coverage_index.load()
                if not success_load:
                    logger.error("Failed to load the newly generated coverage index.")
            else:
                logger.error("Failed to regenerate the coverage index.")
        else:
            logger.info("Coverage index is up-to-date.")
