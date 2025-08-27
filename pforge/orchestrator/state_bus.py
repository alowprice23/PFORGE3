from __future__ import annotations
import orjson
from dataclasses import asdict, dataclass, field
from typing import Dict

from pforge.messaging.in_memory_bus import InMemoryBus

# A simple in-memory cache for the latest state to avoid hitting Redis for every read.
_STATE_CACHE: Dict[str, PuzzleState] = {}


@dataclass
class PuzzleState:
    """Represents the complete, serializable state of the puzzle-solving process at a single point in time."""
    # Core formula components
    gaps: int = 0
    misfits: int = 0
    false_pieces: int = 0
    risk: float = 0.0
    backtracks: int = 0
    entropy: float = 0.0
    phi: int = 0  # Count of successfully removed false pieces

    # Operational metrics
    total_issues: int = 0
    closed_issues: int = 0
    passing_tests: int = 0
    total_tests: int = 0

    # Efficiency score
    efficiency: float = 0.0

    # System state
    tick: int = 0
    qed_reached: bool = False
    last_event_id: str = "0-0"

    # Agent economy
    agent_utility_deltas: Dict[str, float] = field(default_factory=dict)


class StateBus:
    """
    Provides a simple pub/sub facade for the global PuzzleState.
    It publishes state updates to an in-memory bus and keeps a local cache
    for fast, read-only access.
    """
    STATE_STREAM = "pforge:state:global"

    def __init__(self, bus: InMemoryBus):
        self.bus = bus

    def get_snapshot(self, session_id: str = "default") -> PuzzleState:
        """
        Returns a copy of the most recent snapshot of the puzzle state
        from the local cache.
        """
        # Return a copy to prevent mutation of the cached object
        return PuzzleState(**asdict(_STATE_CACHE.get(session_id, PuzzleState())))

    async def publish_update(self, state: PuzzleState, session_id: str = "default"):
        """
        Updates the local cache and publishes the new state to the in-memory bus.
        """
        _STATE_CACHE[session_id] = state

        # Serialize with orjson for performance and correctness
        # In a real system, the message would be an AMPMessage
        await self.bus.publish(self.STATE_STREAM, state)
