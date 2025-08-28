from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import yaml

from .state_bus import StateBus, PuzzleState
from .scheduler import AdaptiveScheduler
from .efficiency_engine import EfficiencyEngine
from .agent_registry import AgentRegistry

logger = logging.getLogger("pforge.orchestrator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

class OrchestratorConfig(dict):
    """Typed wrapper around settings.yaml values."""
    @classmethod
    def load(cls, path: str = "pforge/config/settings.yaml") -> "OrchestratorConfig":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls(raw)

class Orchestrator:
    """Main driver for the pForge agentic system."""

    def __init__(self, cfg: OrchestratorConfig) -> None:
        self.cfg = cfg
        self.state_bus = StateBus()
        self.eff_engine = EfficiencyEngine(cfg.get("formula_constants", {}))
        self.registry = AgentRegistry(self.cfg, self.state_bus, self.eff_engine)
        self.scheduler = AdaptiveScheduler(self.registry, self.state_bus, cfg)

    async def tick(self) -> None:
        """Advance global state then delegate to scheduler."""
        now = datetime.now(timezone.utc)
        puzzle_state = self.state_bus.snapshot()

        puzzle_state.tick += 1
        puzzle_state.timestamp = now.isoformat()

        puzzle_state.efficiency = self.eff_engine.compute(puzzle_state)
        self.state_bus.publish(puzzle_state)

        await self.scheduler.tick(puzzle_state)

        if puzzle_state.efficiency < 0.5:
            logger.warning("Efficiency low (%.2f) – consider user intervention", puzzle_state.efficiency)

    async def run_forever(self) -> None:
        logger.info("Orchestrator started – awaiting ticks")
        while True:
            try:
                await self.tick()
            except Exception as exc:
                logger.exception("Tick failed: %s", exc)
            await asyncio.sleep(1.0)

def start_orchestrator() -> None:
    cfg = OrchestratorConfig.load()
    orch = Orchestrator(cfg)
    asyncio.run(orch.run_forever())

if __name__ == "__main__":
    start_orchestrator()
