from __future__ import annotations
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from pforge.orchestrator.state_bus import PuzzleState

def compute_intelligent_efficiency(state: PuzzleState, constants: Dict[str, float]) -> float:
    """
    Calculates the intelligent puzzle-solving efficiency score (E_intelligent).

    This formula is the mathematical core of pForge, balancing progress against
    the total cost of effort, errors, risk, and complexity.

    E(Σ) = P / (TΣ + Σ[E(t) + γM(t) + αF(t) + D(t)] + λR(Σ) + βB(Σ) + ηH(Σ) - θφ)

    Args:
        state (PuzzleState): The current snapshot of the system state.
        constants (dict): A dictionary of tunable weights for the formula.

    Returns:
        float: The calculated efficiency score, clamped to be non-negative.
    """
    gamma = constants.get("gamma", 1.0)
    alpha = constants.get("alpha", 1.0)
    lambda_ = constants.get("lambda", 2.0)
    beta = constants.get("beta", 1.0)
    eta = constants.get("eta", 1.5)
    theta = constants.get("theta", 2.0)
    delta = constants.get("delta", 0.5) # Used for decay, though decay is passed in state

    # P: Total "pieces" of the puzzle. We can proxy this with the initial number of issues.
    # If not set, we use the current number of open items as a dynamic baseline.
    total_pieces = state.total_issues or (state.gaps + state.misfits + state.false_pieces)
    if total_pieces == 0:
        total_pieces = 1  # Prevent division by zero on a "perfect" project

    # The denominator represents the total "cost" or "effort" expended.
    # It includes time (ticks), errors, complexity, and risk.
    denominator = (
        state.tick  # TΣ: total steps taken
        + state.gaps  # E(t): empty gaps
        + (gamma * state.misfits)  # γM(t): weighted misfits
        + (alpha * state.false_pieces)  # αF(t): weighted false pieces
        + state.decay  # D(t): confidence decay
        + (lambda_ * state.risk)  # λR(Σ): weighted risk
        + (beta * state.backtracks)  # βB(Σ): weighted backtracks
        + (eta * state.entropy)  # ηH(Σ): weighted entropy
        - (theta * state.phi)  # θφ: reward for removing false pieces
    )

    # Ensure the denominator is at least 1 to avoid division by zero or inflation.
    # A score > 1 can be seen as highly efficient, < 1 as inefficient.
    final_score = total_pieces / max(denominator, 1.0)

    return max(0, final_score)
