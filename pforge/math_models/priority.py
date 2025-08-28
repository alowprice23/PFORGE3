from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass
import math

@dataclass
class Task:
    name: str
    priority: float
    time_cost: float
    token_cost: float

def compute_task_priority(impact: float, frequency: float, effort: float, risk: float) -> float:
    """
    Calculates the priority of a fix task based on the formula:
    P = (Impact * Frequency) / (Effort * Risk)
    """
    denominator = (effort * risk) + 1e-6
    return (impact * frequency) / denominator

def cvar(mu: float, sigma: float, alpha: float) -> float:
    """
    Calculates the Conditional Value at Risk (CVaR) for a normal distribution.
    """
    if alpha == 1.0:
        return mu
    # Z-score for the given alpha
    z_alpha = -1.0 * math.sqrt(2) * math.erfcinv(2 * alpha)
    # PDF at z_alpha
    pdf_z_alpha = (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z_alpha**2)
    return mu - sigma * (pdf_z_alpha / (1 - alpha))

def compute_cvar_adjusted_priority(
    impact_mu: float,
    impact_sigma: float,
    effort_mu: float,
    effort_sigma: float,
    risk: float,
    frequency: float,
    alpha: float = 0.90,
) -> float:
    """
    Calculates a risk-adjusted priority using CVaR for impact and effort.
    """
    cvar_impact = cvar(impact_mu, impact_sigma, alpha)
    # For effort, we are interested in the upper tail (bad case), so we use VaR
    var_effort = effort_mu + effort_sigma * (-1.0 * math.sqrt(2) * math.erfcinv(2 * alpha))

    denominator = (var_effort * risk) + 1e-6
    return (cvar_impact * frequency) / denominator

def plan_knapsack(items: List[Dict[str, Any]], budget_time: float, budget_tokens: float) -> List[str]:
    """
    Solves the 0-1 knapsack problem to select the best tasks.
    This is a placeholder for a more sophisticated solver (e.g., using ortools or pulp).
    """
    # Simple greedy approach for now
    sorted_items = sorted(items, key=lambda x: x["priority"] / (x["time_cost"] + 0.001 * x["token_cost"] + 1e-6), reverse=True)

    chosen_tasks = []
    current_time = 0
    current_tokens = 0

    for item in sorted_items:
        if current_time + item["time_cost"] <= budget_time and current_tokens + item["token_cost"] <= budget_tokens:
            chosen_tasks.append(item["name"])
            current_time += item["time_cost"]
            current_tokens += item["token_cost"]

    return chosen_tasks
