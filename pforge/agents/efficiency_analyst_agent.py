from __future__ import annotations
import logging
import asyncio
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message, GapDelta, MisfitDelta, FalsePieceDelta, RiskDelta, BacktrackDelta, EntropyDelta, PhiDelta
from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.orchestrator.efficiency_engine import EfficiencyEngine

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus
    from pforge.config import Config
    from pforge.project import Project

logger = logging.getLogger(__name__)

# The specific delta signals this agent listens to.
DELTA_SIGNALS = [
    MsgType.GAP_DELTA,
    MsgType.MISFIT_DELTA,
    MsgType.FALSE_PIECE_DELTA,
    MsgType.RISK_DELTA,
    MsgType.BACKTRACK_DELTA,
    MsgType.ENTROPY_DELTA,
    MsgType.PHI_DELTA,
]

class EfficiencyAnalystAgent(BaseAgent):
    """
    The designated scorekeeper for the entire system. It consumes all
    delta signals, updates the canonical PuzzleState, re-computes the
    efficiency score, and broadcasts the new state.
    """
    name: str = "efficiency_analyst"
    tick_interval: float = 0.5  # Run frequently to keep state up-to-date

    def __init__(self, bus: InMemoryBus, config: Config, project: Project):
        super().__init__(bus, config, project)
        self.state_bus = StateBus(bus)

        # In a real system, constants would come from a config file.
        # Using placeholder values for now.
        efficiency_constants = {
            "w_g": 1.0, "w_m": 0.5, "w_f": 2.0, "w_r": 0.1,
            "w_b": 5.0, "w_h": 0.2, "w_d": 1.0, "w_phi": 10.0
        }
        self.efficiency_engine = EfficiencyEngine(constants=efficiency_constants)

    async def on_startup(self):
        """Subscribe to all relevant delta signals."""
        self.logger.info("Subscribing to delta signals...")
        for signal_type in DELTA_SIGNALS:
            self.bus.subscribe(self.name, signal_type.value)
        self.logger.info(f"Subscribed to {len(DELTA_SIGNALS)} signal types.")

    async def on_tick(self):
        """
        Process all pending delta signals, update the state, and publish.
        """
        # Get the current state as the baseline for this tick's updates
        current_state = self.state_bus.get_snapshot()
        updated = False

        while True:
            try:
                # Process all available messages without waiting
                message = await self.bus.get(self.name, timeout=0)
                if not message:
                    break  # No more messages in the queue

                updated = self._apply_delta(current_state, message) or updated
            except asyncio.QueueEmpty:
                break # No more messages in the queue

        if updated:
            # If any deltas were applied, re-compute the efficiency score
            current_state.tick += 1
            current_state.efficiency = self.efficiency_engine.compute(current_state)

            # Publish the new canonical state
            await self.state_bus.publish_update(current_state)

            # Also publish a generic metrics update event for other agents
            metrics_message = Message(type=MsgType.METRICS_UPDATED, payload={"tick": current_state.tick})
            await self.publish(MsgType.METRICS_UPDATED.value, metrics_message)
            self.logger.info(f"Published METRICS_UPDATED for tick {current_state.tick} with new efficiency: {current_state.efficiency:.4f}")

    def _apply_delta(self, state: PuzzleState, message: Message) -> bool:
        """Applies a single delta message to the puzzle state."""
        payload = message.payload
        msg_type = message.type

        # This could be more elegant with a map, but is explicit for clarity.
        if msg_type == MsgType.GAP_DELTA:
            state.gaps += payload.get("value", 0)
        elif msg_type == MsgType.MISFIT_DELTA:
            state.misfits += payload.get("value", 0)
        elif msg_type == MsgType.FALSE_PIECE_DELTA:
            state.false_pieces += payload.get("value", 0)
        elif msg_type == MsgType.RISK_DELTA:
            state.risk += payload.get("value", 0)
        elif msg_type == MsgType.BACKTRACK_DELTA:
            state.backtracks += payload.get("value", 0)
        elif msg_type == MsgType.ENTROPY_DELTA:
            state.entropy += payload.get("value", 0)
        elif msg_type == MsgType.PHI_DELTA:
            state.phi += payload.get("value", 0)
        else:
            self.logger.warning(f"Received unhandled message type: {msg_type}")
            return False

        self.logger.debug(f"Applied delta {msg_type} with value {payload.get('value', 0)}")
        return True
