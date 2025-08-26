# PLAN: `agents/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `agents/` directory contains the concrete implementations of all specialized, autonomous agents that constitute the pForge system. Each agent is a distinct, modular service responsible for executing a specific part of the overall puzzle-solving workflow. They are the "workers" who operationalize the mathematical models defined in the `README.md`—they sense, plan, act, and verify. This directory is the embodiment of the "divide and conquer" strategy, breaking down the monolithic task of code repair into manageable, well-defined responsibilities.

**Scope of Ownership**:

*   **Concrete Agent Implementations**: This directory owns the source code for every agent, from the `ObserverAgent` that gathers data to the `FixerAgent` that applies patches and the `QEDSupervisor`'s counterpart agents that verify completion.
*   **Agent-Specific Logic**: All algorithms, heuristics, and business logic unique to an agent's function reside here. For example, the `PredictorAgent`'s logic for updating the risk prior (β) and the `PlannerAgent`'s logic for solving the priority knapsack problem are owned by their respective modules in this directory.
*   **Abstract Base Class (`base_agent.py`)**: It owns the foundational `BaseAgent` class, which defines the common lifecycle, communication hooks (AMP), and operational invariants that all agents must adhere to.
*   **Inter-Agent Communication Contracts (as a client)**: While the `messaging/` directory defines the AMP schema, the agents are the primary clients of this protocol, responsible for correctly constructing, sending, and receiving typed messages.

**Explicitly Not in Scope**:

*   **Agent Lifecycle Management**: The `agents/` directory does not decide *when* an agent should run, be spawned, or be retired. That is the exclusive responsibility of the `orchestrator/scheduler.py`. The agents only respond to lifecycle commands.
*   **Global State Aggregation**: Individual agents publish metric deltas and state changes, but the aggregation of these into the global `PuzzleState` (Σ) and the calculation of system-wide metrics (E, H) is handled by the `orchestrator/efficiency_engine.py`.
*   **Low-Level Implementations**: Agents use tools and clients, but do not own their implementation. For example, they use `llm_clients/` to talk to language models, `tools/` for AST manipulations, and `storage/` for accessing the CAS.
*   **System-Wide Configuration**: While agents consume configuration, the canonical definition and loading of config files (`agents.yaml`, `settings.yaml`) is managed by the `config/` and `pforge/settings.py` modules.

---

## 2. File-by-File Blueprints

This section provides a detailed, implementation-ready blueprint for each of the 16 files in the `agents/` directory.

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `agents/` directory as a Python package and to facilitate the discovery mechanism used by the `agent_registry`. It eagerly imports all agent modules to ensure they are registered.
*   **Data Models**: Exports `AGENT_CLASSES`, a dictionary mapping agent names to their class definitions for tooling and inspection.
*   **Interfaces**: Provides the `BaseAgent` class and `AGENT_CLASSES` dictionary to the `orchestrator/agent_registry.py`.

### 2.2. `base_agent.py`

*   **Responsibilities**:
    *   To define the abstract `BaseAgent` class that all other agents inherit from.
    *   To establish the standard agent lifecycle FSM (`BORN` → `WARMUP` → `ACTIVE` ↔ `QUIESCENT` → `RETIRED`) and provide the corresponding hooks (`on_startup`, `on_tick`, `on_shutdown`).
    *   To provide robust, high-level helper methods for interacting with the AMP bus (`send_amp`, `read_amp`) and publishing metric deltas (`ΔE`, `ΔM`, etc.), abstracting away the raw Redis/fakeredis calls.
    *   To handle boilerplate logic for idempotency, capability checks, and graceful shutdown.
*   **Data Models**: `Phase` (Enum for lifecycle state).
*   **Algorithms**: A core `run_loop` that manages the FSM transitions and calls the `on_tick` hook at a configurable interval, with robust error handling and cancellation logic.
*   **Security**: Will contain a placeholder or hook for checking capability tokens before executing privileged actions.
*   **Tests**: Unit test the lifecycle transitions, the AMP helper methods with mock messages, and the delta publishing helpers.

### 2.3. `observer_agent.py`

*   **Responsibilities**: To be the primary sensor of the pForge system. It continuously observes the state of the sandbox repository and produces the raw data needed for metrics.
    *   It builds and maintains the evidence graph: the dependency graph (G) and test-to-file coverage map (K).
    *   It samples the raw inputs for the Entropy (H) calculation (style vectors, structural metrics).
    *   It runs linters and static analysis tools to count raw issues (gaps).
    *   It publishes all findings as `OBS.TICK` events.
*   **Math Representation**: It computes the raw time-series data `(I_t, H_raw_t, test_outcomes_t)` that feeds the `EfficiencyAnalyst`.
*   **Interfaces**: Consumes file system events. Publishes to the AMP bus. Uses tools from `validation/` and `tools/`.

### 2.4. `spec_oracle_agent.py`

*   **Responsibilities**: To act as the ultimate arbiter of correctness by evaluating the specification constraints (Φ).
    *   It parses specification documents (`docs/`, OpenAPI schemas) to build its internal representation of Φ.
    *   On every significant change (e.g., `FIX.PATCH_APPLIED`), it evaluates every constraint `φ_i ∈ Φ`.
    *   It produces `SPEC.CHECKED` events containing a proof bundle that details which constraints are satisfied and which are violated, including witnesses for each failure.
*   **Math Representation**: It is the direct implementation of the `Φ` evaluation function. Its output is a vector of booleans corresponding to the satisfaction of each `φ_i`.
*   **Interfaces**: Consumes `FIX.PATCH_APPLIED` events. Produces `SPEC.CHECKED` events. May use `proof/` modules to construct its proof bundles.

### 2.5. `predictor_agent.py`

*   **Responsibilities**: To model and predict risk, guiding the Planner away from wasteful actions.
    *   It maintains the risk prior `β_m` for each module `m` in the codebase.
    *   It uses online learning (Bayesian logistic regression) to update `β` based on the outcomes of past fixes (successes vs. rollbacks/conflicts).
    *   It provides the current risk surface to the Planner.
*   **Math Representation**: It implements the learning model for the risk prior `β`.
*   **Interfaces**: Consumes `FIX.PATCH_APPLIED` and `CONFLICT.FOUND` events to learn. Provides risk data to the `PlannerAgent`. Uses `llm_clients/` for its learning model.

### 2.6. `planner_agent.py`

*   **Responsibilities**: To decide what to do next. It is the economic core of pForge.
    *   It consumes the current state (Σ), risk priors (β), and available budgets.
    *   It calculates the priority `P_cvar` for all possible actions.
    *   It solves the budgeted knapsack problem to select the optimal action set A*.
    *   It dispatches `FixTask` and other commands to the appropriate agents.
*   **Math Representation**: It implements the Priority formula `P` and the knapsack optimization.
*   **Interfaces**: Consumes inputs from nearly all other agents (via the state bus). Dispatches tasks to `Fixer`, `Misfit`, etc.

### 2.7. `fixer_agent.py`

*   **Responsibilities**: To execute concrete, safe code transformations.
    *   It receives `FixTask` commands from the Planner.
    *   It uses tools from `tools/` and `llm_clients/` to generate an AST-safe patch.
    *   It runs targeted validation (tests, typechecks) on the patch in a sandbox snapshot.
    *   If validation passes, it emits a `FIX.PATCH_APPLIED` event with a full proof bundle. If not, it emits `FIX.PATCH_REJECTED` with evidence of the failure.
    *   It implements the bounded, risk-aware refinement loop to handle minor failures.
*   **Math Representation**: It applies the transformation `τ` and is responsible for producing the proof that `τ` upholds the relevant constraints in `Φ`.
*   **Interfaces**: Consumes tasks from `Planner`. Uses `tools/`, `validation/`, and `llm_clients/`. Produces patch-related AMP events.

### 2.8. `misfit_agent.py`

*   **Responsibilities**: To reduce stylistic and structural entropy (`H_style`, `H_struct`).
    *   It detects stylistic deviations (e.g., formatting, import order) by comparing file style vectors to the project's mean.
    *   It can be dispatched by the Planner to automatically fix these issues using formatters.
*   **Math Representation**: It is the actuator for reducing the Mahalanobis distance `D_M` of style vectors, thus lowering `H_style`.
*   **Interfaces**: Uses `tools/formatters.py`.

### 2.9. `false_piece_agent.py`

*   **Responsibilities**: To identify and remove extraneous code, dependencies, or other artifacts.
    *   It uses heuristics (reachability analysis, file size) and an LLM-based classifier to find "false pieces".
    *   It proposes removal plans to the Planner, which must be approved before execution.
*   **Math Representation**: It implements the classifier `F(x)` for extraneous pieces and is responsible for the `φ` reward term in the efficiency formula by successfully removing junk.
*   **Interfaces**: Uses the dependency graph from `validation/` and the file system from `sandbox/`.

### 2.10. `backtracker_agent.py`

*   **Responsibilities**: To manage the state space search and execute rollbacks.
    *   When the `ConflictDetector` identifies an unsatisfiable state, the `Backtracker` receives the minimal hitting set of culpable edits.
    *   It uses the `storage/cas.py` to revert the sandbox to the last known good state *before* the conflicting edits were applied.
*   **Math Representation**: It executes the "retract" step in the search algorithm, effectively pruning a bad branch from the A* search tree.
*   **Interfaces**: Consumes events from `ConflictDetector`. Uses `storage/cas.py` to perform rollbacks.

### 2.11. `conflict_detector_agent.py`

*   **Responsibilities**: To find contradictions between applied patches and the specification Φ.
    *   It consumes `SPEC.CHECKED` events that report violations.
    *   It builds a conflict hypergraph mapping violations to the edits that caused them.
    *   It computes the minimal hitting set—the smallest set of edits to retract to resolve the conflict.
*   **Math Representation**: It builds the conflict set Γ and computes the minimal hitting set, a classic set theory problem.
*   **Interfaces**: Consumes events from `SpecOracle`. Produces `CONFLICT.FOUND` events for the `Backtracker`.

### 2.12. `efficiency_analyst_agent.py`

*   **Responsibilities**: The designated scorekeeper for the entire system.
    *   It is the sole consumer of the fine-grained delta signals (`ΔE`, `ΔM`, etc.).
    *   It aggregates these deltas to update the raw metrics in the `PuzzleState`.
    *   It triggers the `efficiency_engine` to recompute the global E and H values.
    *   It is the only agent authorized to emit the `EFF.UPDATED` event.
*   **Math Representation**: It performs the summation part of the `E_intelligent` formula, accumulating the raw error terms before the final calculation.
*   **Interfaces**: Consumes delta signals from all other agents. Triggers `efficiency_engine`.

### 2.13. `intent_router_agent.py`

*   **Responsibilities**: To serve as the natural language interface for the system.
    *   It consumes raw text from the chat UI or CLI.
    *   It uses an LLM with a constrained prompt to classify the user's text into a structured intent (e.g., `{ "intent": "run_fix", "target": "file.py" }`).
    *   It translates this intent into a canonical `user_intent` AMP event for the Planner or other agents to consume.
*   **Math Representation**: It implements the softmax policy over embeddings to classify user intent.
*   **Interfaces**: Consumes user input from `server/`. Publishes intents to the AMP bus. Uses `llm_clients/`.

### 2.14. `recovery_agent.py`

*   **Responsibilities**: To ensure the system's environment is stable *before* code analysis begins.
    *   It orchestrates the preflight checks defined in `recovery/preflight.py`.
    *   It dispatches remediation actions (`env_relock`, `pkg_resolve`, etc.) from `recovery/actions/`.
    *   It guarantees that all prerequisite constraints (`φ_π`) are satisfied before allowing the Planner to work on semantic gaps.
*   **Math Representation**: It is the executor of the prerequisite lattice fixpoint calculation `μ = lfp(F)`.
*   **Interfaces**: Uses modules from the `recovery/` directory.

### 2.15. `self_repair_agent.py`

*   **Responsibilities**: A meta-agent that monitors the health of pForge itself.
    *   It periodically checks for stale indices (coverage, dependency graph) and triggers rebuilds.
    *   It warms up caches after a restart.
    *   It can trigger a self-analysis run, pointing pForge at its own codebase.
*   **Math Representation**: It works to minimize the process entropy (`H_process`) of the pForge system itself.
*   **Interfaces**: Interacts with `validation/` and `storage/` to manage indices and caches.

### 2.16. `summarizer_agent.py`

*   **Responsibilities**: To provide human-readable explanations of the system's actions.
    *   It consumes complex proof bundles and diffs.
    *   It uses an LLM to generate a concise, verifiable summary of what changed and why.
    *   The summary must be grounded in the proof—it cannot invent reasons.
*   **Math Representation**: It translates the formal proof objects into natural language, making the system's reasoning accessible.
*   **Interfaces**: Consumes events from `Fixer` and `Planner`. Produces summary strings for the UI. Uses `llm_clients/`.

---

## 3. Math & Guarantees (from README)

This directory is the direct embodiment of the mathematical framework. Each agent is a "living" implementation of one or more terms from the core formulas.

*   **`E_intelligent(Σ)`**: The entire directory works to optimize this function. `Observer` provides the raw terms. `EfficiencyAnalyst` aggregates them. `Fixer`, `Misfit`, and `FalsePiece` agents perform actions to reduce the error terms (E, M, F). `Planner` selects actions that are expected to yield the largest positive `ΔE`.
*   **Constraints (Φ)**: The `SpecOracleAgent` is the verifier for the entire set of constraints Φ. Its role guarantees that no solution is accepted unless it is formally proven to be correct against the specification.
*   **Conflict Sets (Γ)**: The `ConflictDetectorAgent` and `BacktrackerAgent` directly implement the process of identifying and resolving conflicts, ensuring the search for a solution is logically sound and does not get stuck in contradictory states.
*   **Priority (P) and Risk (β)**: The `PlannerAgent` and `PredictorAgent` work together to implement a risk-aware, value-driven decision engine, ensuring that the system's time and resources are spent on the most promising fixes.

The guarantee of this directory is that the high-level mathematical theory is not just a metaphor; it is the literal instruction set that governs the behavior of every component.

---

## 4. Routing & Awareness

Inter-agent awareness is achieved exclusively through the structured, proof-carrying messages of the AMP bus. There is no direct agent-to-agent communication.

*   **Event-Driven Architecture**: The system is purely event-driven. An agent consumes events, performs its function, and emits new events. This decouples the agents and makes the system highly extensible.
*   **Discovery via State**: An agent becomes "aware" of a situation by observing the global state Σ. For example, the `Planner` becomes aware of a new bug when the `Observer`'s `OBS.TICK` event causes the `gaps` count in Σ to increase.
*   **Coordination through Proofs**: Agents coordinate on complex tasks by passing proofs. The `Fixer` doesn't need to "talk" to the `SpecOracle`; it simply emits a `FIX.PATCH_APPLIED` event with a proof bundle. The `SpecOracle` consumes this event and its proof, performs its own verification, and emits a `SPEC.CHECKED` event. This proof-centric workflow ensures that all collaboration is explicit, auditable, and grounded in verifiable data.

---

## 5. Token & Budget Hygiene

Agents that use LLMs are the primary source of token consumption. The `base_agent.py` will provide a standard mechanism for budget hygiene.

*   **Pre-flight Check**: Before making an LLM call, an agent will call a helper method `self.budget_meter.check_spend(vendor, estimated_tokens)`.
*   **Budget Meter Client**: The `BaseAgent` will be initialized with a client to the `llm_clients/budget_meter.py`.
*   **Graceful Degradation**: If the budget check fails, the agent will not make the LLM call. Instead, it will either fall back to a cheaper, deterministic heuristic or emit an event indicating it is blocked by the budget. For example, the `Fixer` might fall back to a simple AST template instead of a full LLM generation.
*   **Post-facto Reporting**: After an LLM call completes, the agent will report the actual tokens consumed to the budget meter using `self.budget_meter.record_spend(...)`.

This ensures that no single agent can unilaterally exhaust the system's token budget.

---

## 6. Operational Flows

*   **New Bug Found Flow**:
    1.  `ObserverAgent` detects a new failing test. Publishes `OBS.TICK` with updated test outcomes.
    2.  `EfficiencyAnalyst` consumes this, updates the `gaps` count in Σ. Publishes `EFF.UPDATED`.
    3.  `PlannerAgent` consumes the new state, sees the new gap, calculates its priority `P`, and decides it's the next best action.
    4.  `PlannerAgent` dispatches a `FixTask` to the `FixerAgent`.
    5.  `FixerAgent` receives the task, generates a patch, validates it, and publishes `FIX.PATCH_APPLIED` with a proof.
    6.  `ObserverAgent` detects the file change and re-runs the targeted tests. It publishes a new `OBS.TICK` showing the test now passing.
    7.  `EfficiencyAnalyst` consumes this, sees the `gaps` count decrease and `tests_passed` increase, leading to a positive `ΔE`.
*   **Conflict Resolution Flow**:
    1.  `FixerAgent` applies a patch that introduces an import cycle.
    2.  `SpecOracleAgent` consumes the `FIX.PATCH_APPLIED` event and runs its constraint checks. It detects the cycle.
    3.  `SpecOracleAgent` publishes `SPEC.CHECKED` with `sat: false` and a witness identifying the cycle and the culpable patch's `op_id`.
    4.  `ConflictDetectorAgent` consumes this, identifies the single patch as the minimal hitting set. It publishes `CONFLICT.FOUND`.
    5.  `BacktrackerAgent` consumes this and reverts the patch using the CAS. It publishes `BACKTRACK.COMPLETED`.
    6.  The system state is restored, and the `Planner` is now aware (via the `CONFLICT.FOUND` event) that the previous attempt failed and will not retry the same failing strategy.

---

## 7. Testing & Backtests

*   **Unit Tests**: Every agent will be tested in isolation. Mocks for the AMP bus and `PuzzleState` will be used to provide controlled inputs. Tests will assert that for a given input state and event, the agent produces the correct output events and metric deltas. The refinement logic in the `FixerAgent` and the knapsack solver in the `PlannerAgent` will have dedicated, rigorous unit tests.
*   **Integration Tests**:
    *   **Two-Agent Flows**: Tests will cover simple request-response flows, e.g., `Planner` -> `Fixer`, ensuring the contract between them works.
    *   **Full Cycle Tests**: `solve_cycle_test.py` will test the entire loop from bug detection to resolution, involving `Observer`, `Planner`, `Fixer`, and `SpecOracle`.
*   **Backtesting**: The behavior of the entire agent swarm is highly deterministic. A backtest will replay a historical AMP stream and assert that the sequence of agent activations and the final state match the original run, proving the system's deterministic and auditable nature.

---

## 8. Security & Policy

*   **Principle of Least Privilege**: Each agent is granted only the capabilities it needs. This will be enforced by the `BaseAgent`'s interaction with the capability token system. For example, the `ObserverAgent` may only have `fs.read` capability, while the `FixerAgent` is granted temporary `fs.write` and `exec.test` capabilities for a specific task.
*   **Sandboxed Execution**: Agents operate on the `sandbox/` filesystem and do not have access to the host system. The `BaseAgent`'s helpers for file I/O will be hard-coded to use the sandbox root.
*   **Redaction**: Any agent that handles potentially sensitive data (e.g., the `SummarizerAgent` or `ObserverAgent` reading source files) must pass its output through the `proof/redaction.py` service before publishing it to the AMP bus.

---

## 9. Readme Cross-Reference

The agent-based architecture is a direct implementation of the "divide and conquer" strategy discussed in the `README.md`'s "Multi-Agent Solution Framework".

| Agent | README.md Puzzle Analogy |
| :--- | :--- |
| `ObserverAgent` | The person looking at the puzzle, counting the remaining gaps and loose pieces. |
| `SpecOracleAgent` | The person checking if two connected pieces *truly* fit perfectly (color, shape, image). |
| `PlannerAgent` | The person deciding which section of the puzzle to work on next, based on which area looks most promising. |
| `FixerAgent` | The person physically picking up a piece and placing it in a gap. |
| `MisfitAgent` | The person who notices a piece is forced into a spot where the picture doesn't align and straightens it. |
| `FalsePieceAgent` | The person who finds a piece from a different puzzle box and removes it from the table. |
| `BacktrackerAgent` | The person who realizes a whole section was built incorrectly and carefully dismantles it to start over. |
| `ConflictDetectorAgent` | The person who identifies *exactly* which two pieces are causing a section to not fit together. |
| `SummarizerAgent` | The person explaining to a friend what part of the puzzle they just completed. |

This clear mapping ensures that the implementation stays true to the founding mathematical and conceptual principles of the pForge system.
