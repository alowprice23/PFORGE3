# PLAN: `planner/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `planner/` directory is the economic brain of pForge. It is responsible for implementing the logic that decides what the system should do next. It takes the raw data about the state of the system (gaps, misfits, risks, etc.) and uses a mathematical optimization framework to select the most valuable set of actions to perform, given the available resources (time, tokens).

**Scope of Ownership**:

*   **Priority Calculation (`priority.py`)**: It owns the implementation of the `P_cvar` formula, which calculates the risk-adjusted priority of every possible action.
*   **Optimization Solvers (`solver_ilp.py`, `solver_greedy.py`)**: It owns the implementation of the knapsack solvers that select the optimal set of actions to perform, subject to the system's budget constraints. It includes both an exact ILP solver (if available) and a greedy fallback.
*   **Budget Management (`budgets.py`)**: It owns the logic for managing the time and token budgets for the system and for estimating the dual prices of these resources.
*   **Objective Formulation (`objectives.py`)**: It owns the logic for blending multiple objectives (e.g., maximizing `ΔE`, minimizing risk, ensuring stability) into a single objective function for the planner.

**Explicitly Not in Scope**:

*   **Agent Logic**: The `planner/` directory does not contain the logic for the `PlannerAgent`. The agent is the client of the services provided by this directory.
*   **State Management**: It consumes the global `PuzzleState`, but does not own it.
*   **Action Execution**: It decides which actions to perform, but it does not execute them. That is the responsibility of the `FixerAgent` and other operational agents.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `planner/` directory as a Python package.

### 2.2. `priority.py` [ ]

*   **Responsibilities**: To implement the `P_cvar` priority formula.
    *   It takes the impact, frequency, effort, and risk of an action as inputs.
    *   It includes the CVaR formulation to account for uncertainty in the impact and effort estimates.
*   **Math Representation**: This is the direct implementation of the `P_j_cvar` formula.
*   **Interfaces**: Used by the `PlannerAgent` to score all possible actions.

### 2.3. `solver_ilp.py` [ ]

*   **Responsibilities**: To implement the exact knapsack solver using an Integer Linear Programming (ILP) library (e.g., `pulp`).
    *   It takes a list of items (actions) with their priorities and costs as input.
    *   It formulates and solves the 0-1 knapsack problem to find the set of items that maximizes the total priority without exceeding the budgets.
    *   It records the approximation gap (which is 0 for the exact solver).
*   **Interfaces**: Used by the `PlannerAgent`. This module is optional and will only be used if the ILP library is installed.

### 2.4. `solver_greedy.py` [ ]

*   **Responsibilities**: To implement the greedy fallback solver for the knapsack problem.
    *   It sorts the items by their priority-to-cost ratio and adds them to the knapsack until the budgets are exhausted.
    *   It provides an estimate of the approximation gap and the dual prices of the resources.
*   **Algorithms**: Implements a standard greedy algorithm for the knapsack problem.
*   **Interfaces**: Used by the `PlannerAgent` when the ILP solver is not available.

### 2.5. `budgets.py` [ ]

*   **Responsibilities**: To manage the time and token budgets.
    *   It tracks the consumption of time and tokens for each tick.
    *   It estimates the dual prices (shadow prices) of the resources based on their utilization.
*   **Interfaces**: Used by the `PlannerAgent` to get the current budget constraints.

### 2.6. `objectives.py` [ ]

*   **Responsibilities**: To define and blend the multiple objectives of the system.
    *   It provides a way to combine the primary objective of maximizing `ΔE` with other objectives, such as minimizing risk or ensuring stability.
    *   It allows for the dynamic weighting of these objectives based on the current state of the system.
*   **Interfaces**: Used by the `PlannerAgent` to formulate the objective function for the knapsack solver.

---

## 3. Math & Guarantees (from README)

The `planner/` directory is the core of the system's economic decision-making.

*   **Priority Formula**: `priority.py` is the direct implementation of the `P_j_cvar` formula.
*   **Optimization**: The solvers in `solver_ilp.py` and `solver_greedy.py` are the implementation of the budgeted optimization problem that is at the heart of the Planner's decision-making process.
*   **Dual Prices**: The `budgets.py` module provides the dual prices that are used by the `Scheduler` to make decisions about the agent economy.

The guarantee of this directory is that the system will always make rational, value-driven decisions about how to allocate its resources, based on a sound mathematical optimization framework.
