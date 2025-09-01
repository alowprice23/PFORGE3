from __future__ import annotations
from typing import Dict, Any, Callable

def formulate_objective_function(
    weights: Dict[str, float]
) -> Callable[[Dict[str, Any]], float]:
    """
    Creates a function to calculate the overall objective value for an action.

    This function takes a set of weights and returns a scoring function that
    can be applied to any action. The scoring function calculates a weighted
    sum of the action's attributes (e.g., priority, risk).

    Args:
        weights: A dictionary of weights for different objectives.
                 Example: {'priority': 1.0, 'risk': -0.5}
                 A negative weight means the objective should be minimized.

    Returns:
        A function that takes an action (a dictionary of attributes) and
        returns a single scalar objective value.
    """
    def objective_function(action: Dict[str, Any]) -> float:
        """
        Calculates the weighted objective value for a single action.
        """
        total_value = 0.0
        for key, weight in weights.items():
            # Use .get(key, 0) to handle actions that may not have all attributes.
            total_value += weight * action.get(key, 0)
        return total_value

    return objective_function


def get_default_weights(system_state: Dict[str, Any] | None = None) -> Dict[str, float]:
    """
    Provides a default set of weights for the objective function.

    In a more advanced system, these weights could be dynamically adjusted
    based on the overall system state (e.g., become more risk-averse if
    the system is unstable).

    Args:
        system_state: A dictionary representing the current state of the system.
                      (Not used in this simple implementation).

    Returns:
        A dictionary of objective weights.
    """
    # By default, we just want to maximize priority.
    # Risk is assumed to be already incorporated into the priority score.
    return {
        'priority': 1.0,
        'risk': 0.0, # Explicitly not double-counting risk here.
        'effort': 0.0, # Cost is handled by the knapsack, not the objective.
    }
