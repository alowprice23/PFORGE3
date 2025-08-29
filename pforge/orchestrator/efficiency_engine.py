from __future__ import annotations
from typing import TYPE_CHECKING, Dict

from pforge.math_models.efficiency import compute_intelligent_efficiency

if TYPE_CHECKING:
    from pforge.orchestrator.state_bus import PuzzleState


class EfficiencyEngine:
    """
    A wrapper class for the intelligent puzzle-solving efficiency score.
    """

    def __init__(self, constants: Dict[str, float]):
        self.constants = constants

    def compute(self, state: PuzzleState) -> float:
        """
        Computes the efficiency score for the given state.
        """
        return compute_intelligent_efficiency(state, self.constants)
