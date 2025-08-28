from __future__ import annotations
import asyncio
import logging
from enum import Enum, auto
from typing import Any, Dict, Optional
import time

from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.orchestrator.signals import (
    BaseDelta,
    GapDelta,
    MisfitDelta,
    FalsePieceDelta,
    RiskDelta,
    BacktrackDelta,
    EntropyDelta,
)

class Phase(Enum):
    BORN = auto()
    WARM = auto()
    ACTIVE = auto()
    DORMANT = auto()
    RETIRED = auto()

class BaseAgent:
    name: str = "base-agent"
    weight: float = 1.0
    spawn_threshold: float = 0.0
    retire_threshold: float = 0.0
    max_tokens_tick: int = 2_000
    tick_interval: float = 2.0

    def __init__(self, state_bus: StateBus, eff_engine) -> None:
        self.state_bus = state_bus
        self.eff_engine = eff_engine
        self.phase: Phase = Phase.BORN
        self.logger = logging.getLogger(f"agent.{self.name}")
        self._running = True
        self.message_box = []

    async def run_loop(self) -> None:
        self.phase = Phase.WARM
        await self.on_startup()

        self.phase = Phase.ACTIVE
        self.logger.info("Agent %s ACTIVE", self.name)

        while self._running:
            snap: PuzzleState = self.state_bus.snapshot()
            try:
                await self.on_tick(snap)
            except asyncio.CancelledError:
                self.logger.info("Agent %s cancelled", self.name)
                break
            except Exception as exc:
                self.logger.exception("Agent %s tick error: %s", self.name, exc)

            await asyncio.sleep(self.tick_interval)

        self.phase = Phase.RETIRED
        await self.on_shutdown()
        self.logger.info("Agent %s RETIRED", self.name)

    async def stop(self) -> None:
        self._running = False

    async def on_startup(self) -> None:
        return

    async def on_tick(self, state: PuzzleState) -> None:
        raise NotImplementedError

    async def on_shutdown(self) -> None:
        return

    async def send_amp(
        self,
        action: str,
        payload: Dict[str, Any],
        metrics: Optional[Dict[str, float]] = None,
        broadcast: bool = False,
    ) -> None:
        # Simplified in-memory message passing
        # In a real local-only system, this could write to a shared queue
        # or be handled by a central dispatcher.
        # For now, we'll just log it.
        self.logger.debug(f"Sending AMP message: {action} with payload: {payload}")


    async def read_amp(self) -> list[dict[str, Any]]:
        # Simplified in-memory message passing
        messages = self.message_box
        self.message_box = []
        return messages

    async def publish_delta(self, delta: BaseDelta) -> None:
        state = self.state_bus.get_latest_state()
        if delta.kind == "gap":
            state.gaps += delta.value
        elif delta.kind == "misfit":
            state.misfits += delta.value
        elif delta.kind == "false_piece":
            state.false_pieces += delta.value
        elif delta.kind == "risk":
            state.risk += delta.value
        elif delta.kind == "backtrack":
            state.backtracks += delta.value
        elif delta.kind == "entropy":
            state.entropy += delta.value
        self.state_bus.publish(state)


    async def dE(self, value: int) -> None:
        await self.publish_delta(GapDelta(agent=self.name, value=value, ts=time.time()))

    async def dM(self, value: int) -> None:
        await self.publish_delta(MisfitDelta(agent=self.name, value=value, ts=time.time()))

    async def dF(self, value: int) -> None:
        await self.publish_delta(FalsePieceDelta(agent=self.name, value=value, ts=time.time()))

    async def dR(self, value: int) -> None:
        await self.publish_delta(RiskDelta(agent=self.name, value=value, ts=time.time()))

    async def dB(self, value: int) -> None:
        await self.publish_delta(BacktrackDelta(agent=self.name, value=value, ts=time.time()))

    async def dH(self, value: float) -> None:
        await self.publish_delta(EntropyDelta(agent=self.name, value=value, ts=time.time()))
