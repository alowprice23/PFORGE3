from __future__ import annotations

class BudgetManager:
    """
    Manages time and token budgets for an operation.
    """
    def __init__(self, total_time_budget: float, total_token_budget: float):
        self.total_time_budget = total_time_budget
        self.total_token_budget = total_token_budget
        self.spent_time = 0.0
        self.spent_tokens = 0.0

    def record_spend(self, time_spent: float = 0.0, tokens_spent: float = 0.0):
        """
        Records the consumption of resources.
        """
        self.spent_time += time_spent
        self.spent_tokens += tokens_spent

    def get_remaining_budget(self) -> tuple[float, float]:
        """
        Returns the remaining time and token budget.
        """
        remaining_time = self.total_time_budget - self.spent_time
        remaining_tokens = self.total_token_budget - self.spent_tokens
        return max(0, remaining_time), max(0, remaining_tokens)

    def get_utilization(self) -> tuple[float, float]:
        """
        Returns the utilization percentage for time and tokens.
        """
        time_util = self.spent_time / self.total_time_budget if self.total_time_budget > 0 else 1.0
        token_util = self.spent_tokens / self.total_token_budget if self.total_token_budget > 0 else 1.0
        return min(1.0, time_util), min(1.0, token_util)

    def estimate_dual_prices(self, base_price: float = 1.0, steepness: float = 5.0) -> dict[str, float]:
        """
        Estimates the dual prices (shadow prices) of resources based on utilization.

        The price of a resource increases exponentially as it becomes more scarce.
        This heuristic helps the planner prioritize actions that use less of a
        constrained resource.

        Args:
            base_price: The base price when the resource is not utilized.
            steepness: A factor to control how quickly the price increases.

        Returns:
            A dictionary with the estimated prices for 'time' and 'tokens'.
        """
        time_util, token_util = self.get_utilization()

        # Exponentially increase price with utilization
        time_price = base_price * (1 + (steepness ** time_util - 1) / (steepness - 1))
        token_price = base_price * (1 + (steepness ** token_util - 1) / (steepness - 1))

        return {"time": time_price, "tokens": token_price}
