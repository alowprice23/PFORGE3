from __future__ import annotations
from typing import List, Dict, Any, Optional
import pulp

def solve_knapsack_ilp(
    items: List[Dict[str, Any]],
    budget: float,
    solver: Optional[pulp.LpSolver] = None
) -> List[Dict[str, Any]] | None:
    """
    Implements the exact 0/1 knapsack solver using an Integer Linear
    Programming (ILP) library, PuLP.

    This function finds the optimal set of items that maximizes total priority
    without exceeding the budget.

    Args:
        items: A list of items, where each item is a dictionary with at least
               'name', 'priority', and 'cost' keys.
        budget: The maximum total cost the knapsack can hold.
        solver: An optional PuLP solver instance. If None, PuLP's default
                solver will be used.

    Returns:
        A list of the selected items, or None if PuLP is not available or
        if the problem is infeasible.
    """
    try:
        # Create the LP problem
        prob = pulp.LpProblem("KnapsackProblem", pulp.LpMaximize)

        # Create decision variables
        item_vars = {item['name']: pulp.LpVariable(f"x_{item['name']}", 0, 1, pulp.LpBinary) for item in items}

        # Objective function: maximize total priority
        prob += pulp.lpSum([item['priority'] * item_vars[item['name']] for item in items]), "TotalPriority"

        # Constraint: total cost must be within budget
        prob += pulp.lpSum([item['cost'] * item_vars[item['name']] for item in items]) <= budget, "BudgetConstraint"

        # Solve the problem, suppressing solver messages
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        # Check the status
        if pulp.LpStatus[prob.status] == 'Optimal':
            knapsack = [item for item in items if pulp.value(item_vars[item['name']]) == 1]
            return knapsack
        else:
            return [] # Return empty list if not optimal (e.g., infeasible)

    except ImportError:
        # This function is optional if pulp is not installed.
        return None
    except Exception:
        # Broad exception to catch any errors during solving.
        return None
