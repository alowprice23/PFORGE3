from __future__ import annotations
import numpy as np

def calculate_priority(
    impact: float,
    frequency: float,
    effort: np.ndarray, # Distribution of effort costs
    risk_score: float = 0.0,
    in_conflict: bool = False,
    risk_percentile: float = 0.95
) -> float:
    """
    Calculates the priority of an action using a risk-adjusted formula.

    The formula is, conceptually:
    P = (Impact * Frequency) / (Adjusted_Effort * Risk_Factor * Conflict_Factor)

    CVaR (Conditional Value at Risk) is used to provide a risk-adjusted
    measure of the effort. It represents the average cost of the worst-case
    scenarios.

    Args:
        impact: The estimated positive impact of the action.
        frequency: The frequency of the event this action addresses.
        effort: A numpy array representing the distribution of possible
                effort costs (e.g., from multiple LLM estimates).
        risk_score: A direct risk score (e.g., from the PredictorAgent).
        in_conflict: A boolean indicating if the task is part of a conflict.
        risk_percentile: The percentile for calculating VaR (Value at Risk),
                         which is the basis for CVaR. E.g., 0.95 for the 95th
                         percentile.

    Returns:
        The calculated priority score. Higher is better.
    """
    if effort.size == 0:
        return 0.0

    # Value at Risk (VaR): the cost at the specified percentile.
    var = np.percentile(effort, risk_percentile * 100)

    # Conditional Value at Risk (CVaR): the average of costs exceeding VaR.
    cvar_effort = effort[effort >= var].mean()

    # Incorporate the direct risk score and conflict status.
    # We add 1 to risk_score to avoid multiplying by zero.
    risk_factor = 1 + risk_score
    # Penalize tasks in conflict significantly.
    conflict_factor = 2.0 if in_conflict else 1.0

    denominator = cvar_effort * risk_factor * conflict_factor

    # If the denominator is zero or negligible, avoid division by zero.
    if denominator < 1e-6:
        # If impact is positive, this is an infinitely good action.
        return float('inf') if impact > 0 else 0.0

    priority = (impact * frequency) / denominator
    return priority
