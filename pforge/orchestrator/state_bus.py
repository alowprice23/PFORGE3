from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Dict, Any

@dataclass
class PuzzleState:
    tick: int = 0
    gaps: int = 0
    misfits: int = 0
    false_pieces: int = 0
    risk: float = 0.0
    backtracks: int = 0
    entropy: float = 0.0
    phi: int = 0
    efficiency: float = 0.0
    solved: bool = False
    delta_utility: Dict[str, float] = field(default_factory=dict)
    timestamp: str | None = None
    total_issues: int = 0
    decay: float = 0.0

class StateBus:
    def __init__(self):
        self._snap_cache: PuzzleState = PuzzleState()

    def snapshot(self) -> PuzzleState:
        """Return a mutable copy of the last state."""
        # Ensure that _snap_cache is always a PuzzleState instance before calling asdict
        if not isinstance(self._snap_cache, PuzzleState):
             # This can happen if publish was called with a dict.
             # We can try to recover or, for robustness, reset to a default state.
             self._snap_cache = PuzzleState()
        return PuzzleState(**asdict(self._snap_cache))

    async def publish(self, state: PuzzleState) -> None:
        """Updates the in-memory state."""
        if not isinstance(state, PuzzleState):
            raise TypeError(f"StateBus.publish() expected a PuzzleState object, but got {type(state)}")
        self._snap_cache = state

    def get_latest_state(self) -> PuzzleState:
        """Returns the latest state."""
        return self.snapshot()
