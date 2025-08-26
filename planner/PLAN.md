# PLAN: `planner/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `planner/` directory is the economic decision-making engine of the pForge system. Its sole purpose is to answer the question: "Given the current state of the system, the outstanding issues, the associated risks, and our limited resources, what is the most valuable set of actions to take right now?" It does this by quantitatively scoring all potential actions and selecting an optimal, budgeted subset to be executed by the other agents.

**Scope of Ownership**:

*   **Priority Calculation (`priority.py`)**: It owns the canonical implementation of the Priority formula `P = (Impact * Frequency) / (Effort * Risk)` and its risk-adjusted CVaR (Conditional Value at Risk) variant. This is the heart of its decision-making logic.
*   **Optimization Solvers (`solver_ilp.py`, `solver_greedy.py`)**: It contains the algorithms for solving the budgeted action selection problem, which is modeled as a 0-1 knapsack problem. This includes a preferred exact solver (Integer Linear Programming) and a mandatory, robust fallback (greedy heuristic).
*   **Budget Management (`budgets.py`)**: It is responsible for taking the high-level time and token budgets provided by the `Orchestrator` and applying them as hard constraints within its optimization problem. It also estimates the economic "shadow prices" (duals) of these constraints.
*   **Objective Formulation (`objectives.py`)**: It defines the objective function for the optimization. While the primary objective is to maximize total priority, this module allows for future extensions, such as multi-objective blends (e.g., balancing `ΔE` maximization with `ΔH` minimization).

**Explicitly Not in Scope**:

*   **Action Execution**: The `planner/` directory **only plans**; it does not execute. The execution of the plan (e.g., applying a code patch) is the responsibility of the `FixerAgent` and other operational agents.
*   **Candidate Generation**: The planner does not generate the list of possible actions. It consumes candidate actions proposed by other agents like the `PredictorAgent` (proposing stubs) or `MisfitAgent` (proposing format fixes).
*   **Metric Calculation**: It consumes metrics like Impact, Frequency, Effort, and Risk, but it does not calculate them. These are provided by the `EfficiencyAnalyst`, `PredictorAgent`, and `FixerAgent` (reporting on actual effort).
*   **Global State Management**: It is a client of the global state Σ but does not own or manage it. That is the `orchestrator/`'s role.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `planner/` directory as a Python package and re-export key functions like `plan_knapsack` for easy use by the `PlannerAgent`.
*   **Interfaces**: Provides the main entry point for the `PlannerAgent`.

### 2.2. `priority.py`

*   **Responsibilities**:
    *   To provide a robust, tested implementation of the action-priority scoring formulas.
    *   To define the `Item` dataclass, a structured representation of a candidate action, including its name and all features required for scoring (Impact, Frequency, Effort, Risk, and their distributions).
    *   To implement the CVaR calculation to adjust priority based on the uncertainty (variance) of impact and effort estimates.
*   **Data Models**:
    *   `Item(name: str, impact_dist: tuple, effort_dist: tuple, freq: float, risk: float)` where distributions are `(mean, variance)`.
*   **Algorithms**:
    *   `calculate_priority(item: Item) -> float`: The baseline `P` formula.
    *   `calculate_cvar_priority(item: Item, alpha: float) -> float`: The advanced `P_cvar` formula, using the Gaussian CVaR formula to handle uncertainty.
*   **Tests**: Rigorous unit tests for both priority formulas with a variety of inputs, including edge cases (zero risk, zero effort) and known distributions to verify the CVaR calculation.

### 2.3. `solver_ilp.py`

*   **Responsibilities**:
    *   To provide the preferred, high-precision solver for the 0-1 knapsack problem.
    *   To use an external Integer Linear Programming (ILP) library like `pulp` or `ortools` if it is available in the environment.
    *   To formulate the problem correctly: setting the objective function to `sum(P_j * x_j)` and adding the two budget constraints for time and tokens.
    *   To return an exact solution, including the chosen items, the optimal objective value, and the true dual prices of the constraints.
*   **Inputs/Outputs**:
    *   Inputs: A list of `Item` objects and two budget floats (`B_time`, `B_tokens`).
    *   Outputs: A `PlanResult` object with `approx_gap=0.0`.
*   **Edge Cases**: If the ILP library is not installed, this module should fail gracefully (e.g., return `None` or raise a specific `SolverUnavailableError`), allowing the system to fall back to the greedy solver.
*   **Tests**: Unit test with a small, known knapsack problem to verify that the ILP formulation is correct and returns the optimal solution.

### 2.4. `solver_greedy.py`

*   **Responsibilities**:
    *   To provide a mandatory, fast, and robust fallback solver that works in all environments (no external dependencies).
    *   To implement a greedy heuristic for the knapsack problem, typically by sorting items by their "value-to-cost" ratio (`P / (α*t + β*k)`).
    *   To return a `PlanResult` that explicitly flags the solution as approximate by setting a non-zero `approx_gap`.
    *   To provide a reasonable *estimate* of the dual prices based on the final resource utilization.
*   **Inputs/Outputs**:
    *   Inputs: A list of `Item` objects and two budget floats.
    *   Outputs: A `PlanResult` object with `approx_gap > 0.0`.
*   **Algorithms**: Greedy algorithm for the 0-1 knapsack problem.
*   **Tests**: Unit test with a small knapsack problem where the greedy algorithm is known to produce a suboptimal result, and verify that the output is correct for the greedy approach and that the `approx_gap` is set.

### 2.5. `budgets.py`

*   **Responsibilities**:
    *   To define the `PlanResult` dataclass, which is the canonical output structure for all solvers.
    *   To contain helper functions for budget accounting and the estimation of dual prices for the greedy solver.
*   **Data Models**:
    *   `PlanResult(chosen: list[str], objective: float, duals: dict, approx_gap: float, budget: dict)`.
*   **Algorithms**: The dual price estimation for the greedy solver can be a simple function of utilization: `dual = utilization / (1 - utilization + ε)`. This heuristic captures the intuition that a resource's shadow price is high when it is nearly fully used.
*   **Tests**: Unit test the dual price estimation heuristic.

### 2.6. `objectives.py`

*   **Responsibilities**:
    *   To define the objective function used by the solvers.
    *   Initially, this will be a simple summation of the priorities of the chosen items: `sum(P_j * x_j)`.
    *   This module is designed for extensibility, allowing for the future introduction of more complex, multi-objective functions (e.g., `maximize(ΔE) - λ*minimize(ΔH)`).
*   **Data Models**: `ObjectiveFunction` (a callable class or function).
*   **Tests**: Unit test that the objective function correctly calculates the total priority of a given set of items.

---

## 3. Math & Guarantees (from README)

The `planner/` directory is the most direct and crucial implementation of the system's economic reasoning.

*   **Priority `P` and `P_cvar`**: `priority.py` provides the canonical, tested implementation of these formulas. This guarantees that the system's notion of "value" is consistent and grounded in the agreed-upon mathematical model.
*   **Optimization under Constraints**: The solvers (`solver_ilp.py`, `solver_greedy.py`) guarantee that the system's actions are not just valuable but also feasible. They ensure that pForge never creates a plan that violates its resource budgets.
*   **Approximation Guarantees**: By forcing the greedy solver to report an `approx_gap`, the system maintains intellectual honesty. It knows when its plan is optimal versus when it is a good-faith heuristic. This information is passed up in the proof bundle, so the `QEDSupervisor` or a human operator can understand the level of certainty behind a plan.

The primary guarantee of this directory is **rational resource allocation**: pForge will always use its time and tokens to work on the highest-priority tasks it can afford, based on a quantitative and auditable model of value.

---

## 4. Routing & Awareness

The planner's awareness is primarily economic and risk-based, not structural.

*   **Risk Awareness**: It is aware of which parts of the codebase are risky (`β`) because it receives this information as an input to the `P` formula. It will naturally de-prioritize changes in high-risk modules unless their potential impact is massive.
*   **Resource Awareness**: It is aware of resource scarcity through its budgets. The dual prices it calculates are a direct measure of this scarcity, which it can pass to the `Scheduler` to inform longer-term resource allocation strategies (e.g., spawning more of a certain agent type).
*   **Goal Awareness**: The planner is fundamentally goal-aware because its objective function (`sum(P_j * x_j)`) is a direct proxy for the system's goal of making progress (`ΔE`).

It does not perform file-level routing, but it consumes the output of the `orchestrator/router.py` to understand the full scope (and thus, the full effort and risk) of a proposed change.

---

## 5. Token & Budget Hygiene

This directory is the **enforcement mechanism** for budget hygiene. The `Orchestrator` sets the policy (the budget numbers), but the `planner/` solvers are where that policy is mathematically enforced as a hard constraint in the optimization. A well-behaved planner in this architecture *cannot* produce a plan that exceeds the budget. This is a powerful guarantee against runaway costs.

---

## 6. Operational Flows

1.  **Trigger**: The `PlannerAgent` is triggered by the `Scheduler`.
2.  **Gather**: The agent gathers a list of candidate `Item`s from other agents' signals (e.g., `Predictor`'s suggestions).
3.  **Score**: It calls `priority.py` to calculate `P_cvar` for each item.
4.  **Constrain**: It gets the current `B_time` and `B_tokens` from `budgets.py`.
5.  **Solve**: It passes the scored items and budgets to the solver stack. It first tries `solver_ilp.py`. If that fails (e.g., library not installed), it calls `solver_greedy.py`.
6.  **Result**: It receives a `PlanResult` object.
7.  **Publish**: The `PlannerAgent` wraps this result in a `PLAN.PROPOSED` AMP event, including the `duals` and `approx_gap` in the proof bundle, and publishes it.

---

## 7. Testing & Backtests

*   **Unit Tests**: As described above, each module will have focused unit tests for its mathematical functions and algorithms.
*   **Integration Tests**: A key integration test will be `test_planner_end_to_end`, which creates a mock set of candidate items, passes them to the main planning function, and asserts that the returned `PlanResult` is correct and consistent, regardless of which solver was used.
*   **Backtesting**: The planner's performance can be backtested by replaying historical sessions. The verifier script will:
    1.  Take the `PLAN.PROPOSED` events from the log.
    2.  For each, look at the subsequent `FIX.PATCH_APPLIED` events that were caused by that plan.
    3.  Calculate the *actual* `ΔE` that resulted from the plan.
    4.  Compare the planner's *predicted* objective value with the *actual* `ΔE`. A good planner will have a high correlation between the two. This feedback can be used to tune the weights in the `P` formula.

---

## 8. Security & Policy

The planner is a potential target for manipulation. A malicious agent could try to feed it fake candidate items with artificially high `Impact` or low `Risk` scores to trick it into prioritizing harmful actions. The planner's defenses are:

*   **Trust, but Verify**: The planner should operate on the assumption that the inputs it receives are generated in good faith, but its outputs are always subject to verification by the `SpecOracle`. Even if the planner prioritizes a malicious fix, the `SpecOracle`'s constraint checks should block it from being accepted.
*   **Proof Trail**: The `PLAN.PROPOSED` proof bundle makes the planner's reasoning transparent. If it makes a strange decision, an auditor can inspect the proof to see the input scores and dual prices that led to that decision, making it possible to trace the manipulation back to its source.

---

## 9. Readme Cross-Reference

The `planner/` directory directly implements the strategic decision-making aspect of the puzzle-solving framework from the `README.md`.

| Planner Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `priority.py` | The implementation of the "ultimate formula" component that balances risk, effort, and reward to decide on the next move. |
| `solver_*.py` | Represents the solver's cognitive process of choosing from many possible moves (placing pieces) while being constrained by limited time and energy (the budgets). |
| `budgets.py` | The formal representation of the "cognitive constraints" or "finite-time limiters" discussed to prevent getting stuck in infinite loops. |

The planner is the part of the system that embodies the shift from a random, brute-force search to an intelligent, value-driven search for the solution.
