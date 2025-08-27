# PLAN: `orchestrator/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `orchestrator/` directory is the central nervous system of pForge. It is responsible for driving the main event loop, managing the lifecycle of all agents, and ensuring that the system as a whole makes progress towards a solved state. It is the implementation of the "Coordinator (Executive) Agent" described in the `README.md`, but it is more than a simple script; it is a sophisticated, stateful service that orchestrates the entire puzzle-solving process.

**Scope of Ownership**:

*   **Main Event Loop (`core.py`)**: It owns the primary "tick" loop that drives the entire system. On each tick, it gathers a snapshot of the global state (Σ), triggers the scheduler, and advances the system's clock.
*   **Agent Lifecycle Management (`scheduler.py`, `agent_registry.py`)**: It is responsible for discovering, instantiating, spawning, and retiring all agents based on the principles of the adaptive agent economy.
*   **State Management (`state_bus.py`)**: It owns the in-memory representation of the global `PuzzleState` and the facade for publishing state changes to the AMP bus.
*   **Efficiency Calculation (`efficiency_engine.py`)**: It owns the implementation of the `E_intelligent` formula, which is the core objective function for the entire system.
*   **Event Definitions (`signals.py`)**: It defines the canonical data structures for all AMP events, ensuring type safety and consistency across the system.
*   **Completion Supervision (`qedsupervisor.py`)**: It owns the logic for determining when the system has reached a "done" state (QED), based on the satisfaction of all blocking constraints and the stability of the efficiency metric.
*   **Logical Routing (`router.py`)**: It owns the high-level routing logic that helps the Planner decide whether to apply a fix to a single file or an entire directory, based on the dependency graph.

**Explicitly Not in Scope**:

*   **Agent-Specific Logic**: The `orchestrator/` does not contain the business logic for any of the specialized agents. That resides in the `agents/` directory.
*   **Low-Level Implementations**: It does not own the implementation of the storage, messaging, or validation layers. It uses the APIs provided by those directories.
*   **Configuration**: It consumes configuration, but the definition and loading of config files is handled by the `config/` and `pforge/settings.py` modules.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `orchestrator/` directory as a Python package and to re-export its public symbols for convenient access.

### 2.2. `core.py` [x]

*   **Responsibilities**:
    *   To implement the main `Orchestrator` class and the `run_forever` tick loop.
    *   To load the system configuration.
    *   To initialize all major components (StateBus, Scheduler, etc.).
    *   On each tick, to create the global state snapshot (Σ), advance the system clock, and trigger the `Scheduler`.
    *   To provide the `lifespan` context manager for the FastAPI application.
*   **Algorithms**: The core of this file is the main event loop, which is a simple `while True` loop with a sleep interval.
*   **Interfaces**: It is the top-level entry point for the backend application.

### 2.3. `scheduler.py` [x]

*   **Responsibilities**: To implement the adaptive agent economy.
    *   On each tick, it computes a utility score for every registered agent based on its weight and its recent contribution to `ΔE`.
    *   It compares this utility score to the `spawn_threshold` and `retire_threshold` defined in `config/agents.yaml`.
    *   It makes decisions to spawn, retain, or retire agents and executes these decisions by creating or cancelling asyncio tasks.
    *   It includes the PI controller for managing concurrency and throttling.
*   **Math Representation**: It is the direct implementation of the agent utility function `U_a(t)` and the concurrency control logic.
*   **Interfaces**: Consumes the `PuzzleState` from the `StateBus`. Interacts with the `AgentRegistry` to instantiate agents.

### 2.4. `agent_registry.py` [x]

*   **Responsibilities**: To act as a service locator and factory for all agents.
    *   It discovers all `BaseAgent` subclasses in the `agents/` directory using `pkgutil`.
    *   It stores the metadata for each agent (name, weight, thresholds).
    *   It provides a method to instantiate a new agent by name, injecting its dependencies (StateBus, EfficiencyEngine).
*   **Interfaces**: Used by the `Scheduler` to create new agent instances.

### 2.5. `state_bus.py` [x]

*   **Responsibilities**: To manage the in-memory `PuzzleState`.
    *   It defines the `PuzzleState` dataclass, which is the canonical representation of the system's state at any given moment.
    *   It provides a `snapshot()` method to get a mutable copy of the current state.
    *   It provides a `publish()` method to write the updated state to the Redis/fakeredis stream.
*   **Interfaces**: Used by almost every component in the system to get the current state.

### 2.6. `efficiency_engine.py` [x]

*   **Responsibilities**: To implement the core mathematical formula for system efficiency.
    *   It takes a `PuzzleState` object as input.
    *   It computes the `E_intelligent` score based on the formula from the `README.md` and the constants from `config/settings.yaml`.
*   **Math Representation**: This is the direct, line-by-line implementation of the `E_intelligent(Σ)` formula.
*   **Interfaces**: Used by `core.py` to update the efficiency score on each tick.

### 2.7. `signals.py` [x]

*   **Responsibilities**: To define the typed dataclasses for all the fine-grained delta signals (e.g., `GapDelta`, `MisfitDelta`) that agents can emit.
*   **Interfaces**: These dataclasses are used throughout the system to create and parse AMP messages.

### 2.8. `qedsupervisor.py` [ ]

*   **Responsibilities**: To determine when the puzzle is "solved".
    *   It consumes `SPEC.CHECKED` and `EFF.UPDATED` events.
    *   It maintains a sliding window of recent states to check for stability.
    *   It enforces the QED predicate: all blocking constraints satisfied, efficiency stable and above target, and no open conflicts.
    *   When the predicate is met, it co-signs a proof bundle and emits the final `QED.EMITTED` event.
*   **Math Representation**: Implements the `QED(Σ)` completion predicate.
*   **Interfaces**: Consumes events from the AMP bus. Emits the final `QED.EMITTED` event.

### 2.9. `router.py` [ ]

*   **Responsibilities**: To provide high-level routing advice to the `PlannerAgent`.
    *   When the `Planner` is considering a fix, the `Router` can analyze the dependency graph to determine the "blast radius" of the change.
    *   It can recommend whether a fix should be applied to a single file or if a whole directory or subsystem should be considered for a refactor.
*   **Algorithms**: Uses graph traversal algorithms on the dependency graph from `validation/`.
*   **Interfaces**: Provides a service to the `PlannerAgent`.

---

## 3. Math & Guarantees (from README)

The `orchestrator/` is the engine that drives the entire mathematical optimization process.

*   `efficiency_engine.py` is the heart of the system, implementing the objective function.
*   `scheduler.py` implements the utility-based decision-making that is a core part of the agentic economy.
*   `qedsupervisor.py` implements the formal completion predicate, providing a mathematical guarantee that "done" means "provably correct".

The guarantee of this directory is that the system will be driven in a principled, stateful, and convergent manner, always working to optimize the objective function `E` until the completion state `QED` is reached.
