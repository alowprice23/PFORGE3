from __future__ import annotations
from typing import List, Dict, Any

def solve_knapsack_greedy(items: List[Dict[str, Any]], budget: float) -> List[Dict[str, Any]]:
    """
    Implements the greedy fallback solver for the 0/1 knapsack problem.

    This function sorts items by their priority-to-cost ratio and adds them
    to the knapsack until the budget is exhausted.

    Args:
        items: A list of items, where each item is a dictionary with at least
               'name', 'priority', and 'cost' keys.
        budget: The maximum total cost the knapsack can hold.

    Returns:
        A list of the items selected to be in the knapsack.
    """
    # Calculate priority-to-cost ratio, handling potential zero cost.
    for item in items:
        cost = item.get('cost', 0)
        priority = item.get('priority', 0)
        if cost > 0:
            item['ratio'] = priority / cost
        else:
            # If cost is zero and priority is positive, it's infinitely valuable.
            item['ratio'] = float('inf') if priority > 0 else 0

    # Sort items by the ratio in descending order.
    sorted_items = sorted(items, key=lambda x: x['ratio'], reverse=True)

    knapsack = []
    current_cost = 0.0

    for item in sorted_items:
        cost = item.get('cost', 0)
        if current_cost + cost <= budget:
            knapsack.append(item)
            current_cost += cost

    return knapsack
