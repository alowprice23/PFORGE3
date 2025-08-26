from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state_bus import PuzzleState

class EfficiencyEngine:
    """
    Implements the pForge Efficiency Formula (E_intelligent).

    This engine calculates the system's overall efficiency score based on the
    current PuzzleState, weighting factors for progress, and penalties for
    disorder and wasted effort.
    """

    def __init__(self, constants: dict):
        """
        Initializes the engine with tunable constants from the system config.

        Args:
            constants (dict): A dictionary containing the formula's weights,
                              e.g., from config/policies.yaml.
        """
        # Weights for the positive components (progress)
        self.w_issues = constants.get("w_issues", 0.6)
        self.w_tests = constants.get("w_tests", 0.4)

        # Weights for the negative components (penalties)
        self.w_entropy = constants.get("w_entropy", 0.2)
        self.w_risk = constants.get("w_risk", 0.1)
        self.w_backtracks = constants.get("w_backtracks", 0.1)

        # Reward for removing false pieces
        self.w_phi = constants.get("w_phi", 2.0)

    def compute(self, state: PuzzleState) -> float:
        """
        Calculates the efficiency score E for the given PuzzleState.

        E = (w1 * Progress_Issues + w2 * Progress_Tests) -
            (w3 * H + w4 * R + w5 * B) +
            (w6 * φ)

        Args:
            state (PuzzleState): The current snapshot of the system state.

        Returns:
            float: The calculated efficiency score.
        """

        # --- Progress Terms ---
        # Progress in closing issues (value between 0 and 1)
        if state.total_issues > 0:
            progress_issues = state.closed_issues / state.total_issues
        else:
            progress_issues = 1.0  # If no issues, progress is 100%

        # Progress in passing tests (value between 0 and 1)
        if state.total_tests > 0:
            progress_tests = state.passing_tests / state.total_tests
        else:
            progress_tests = 1.0 # If no tests, test progress is 100%

        positive_score = (self.w_issues * progress_issues) + (self.w_tests * progress_tests)

        # --- Penalty Terms ---
        # Penalties are normalized by the number of ticks to avoid unbounded growth
        # and represent the "cost per tick" of these negative factors.
        ticks = max(1, state.tick)

        penalty_entropy = self.w_entropy * state.entropy
        penalty_risk = self.w_risk * (state.risk / ticks)
        penalty_backtracks = self.w_backtracks * (state.backtracks / ticks)

        negative_score = penalty_entropy + penalty_risk + penalty_backtracks

        # --- Reward Term ---
        # Reward for removing false pieces, also normalized by ticks.
        reward_phi = self.w_phi * (state.phi / ticks)

        # --- Final Score ---
        # The score is clamped to be non-negative.
        final_score = max(0, positive_score - negative_score + reward_phi)

        return final_score
