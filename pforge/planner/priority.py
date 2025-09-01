from __future__ import annotations
import numpy as np

def calculate_priority(
    impact: float,
    frequency: float,
    effort: np.ndarray, # Distribution of effort costs
    risk_percentile: float = 0.95
) -> float:
    """
    Calculates the priority of an action using a CVaR-like formula.

    The formula is: P = (Impact * Frequency) / CVaR(Effort)

    CVaR (Conditional Value at Risk) is used to provide a risk-adjusted
    measure of the effort. It represents the average cost of the worst-case
    scenarios.

    Args:
        impact: The estimated positive impact of the action.
        frequency: The frequency of the event this action addresses.
        effort: A numpy array representing the distribution of possible
                effort costs (e.g., from multiple LLM estimates).
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

    # If CVaR is zero or negligible, avoid division by zero.
    if cvar_effort < 1e-6:
        # If impact is positive, this is an infinitely good action.
        return float('inf') if impact > 0 else 0.0

    priority = (impact * frequency) / cvar_effort
    return priority
