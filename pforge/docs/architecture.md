# pForge System Architecture

## 1. High-Level Overview

pForge is an AI-powered, local-first code repair and refactoring engine designed as a multi-agent, puzzle-solving system. Its architecture is fundamentally **event-driven**, **mathematically governed**, and **proof-carrying**. The system treats a codebase as a puzzle with a desired "solved" state, and it coordinates a team of specialized AI agents to reach that state in a predictable, auditable, and efficient manner.

The core architectural principles are:

*   **Divide and Conquer**: The complex problem of code repair is broken down into smaller, well-defined tasks, each handled by a specialized agent.
*   **Event-Driven Communication**: Agents are decoupled and communicate asynchronously via a central message bus (AMP), making the system extensible and resilient.
*   **Mathematical Governance**: The system's actions are not based on heuristics alone but are governed by a formal mathematical framework that defines efficiency (E), entropy (H), priority (P), and risk (β).
*   **Proof-of-Work**: No action is considered complete without a verifiable, cryptographic proof. This ensures that every step is auditable and the system's claims of progress are trustworthy.
*   **Content-Addressable Storage**: All code states are managed in a Content-Addressable Store (CAS), providing immutable, verifiable snapshots of the codebase at every stage.

## 2. Core Components

The pForge system is composed of four primary components: the **Orchestrator**, the **Agent Swarm**, the **Messaging Bus**, and the **Storage Layer**.

![Component Diagram](https://i.imgur.com/example.png "pForge High-Level Component Diagram")
*Figure 1: A high-level diagram showing the interaction between the core components.*

### 2.1. The Orchestrator

The Orchestrator is the central nervous system of pForge. It is responsible for driving the main event loop, managing the lifecycle of all agents, and ensuring the system makes coherent progress.

*   **Main Event Loop (`core.py`)**: The `Orchestrator` runs a continuous "tick" loop. On each tick, it creates a global snapshot of the system state (Σ), triggers the `Scheduler`, and advances the system's clock.
*   **Agent Lifecycle Management (`scheduler.py`, `agent_registry.py`)**: It implements an "adaptive agent economy," deciding which agents to spawn, keep active, or retire based on their utility and the system's current needs.
*   **State Management (`state_bus.py`)**: It maintains the canonical, in-memory `PuzzleState` and provides a facade for publishing state changes to the message bus.
*   **Efficiency Engine (`efficiency_engine.py`)**: It is the direct implementation of the system's core objective function, `E_intelligent(Σ)`, which quantifies the health and correctness of the codebase.
*   **QED Supervisor (`qedsupervisor.py`)**: It is the ultimate arbiter of "doneness." It enforces the completion predicate (QED), ensuring that all blocking constraints are satisfied and the system is stable before declaring success.

### 2.2. The Agent Swarm

The Agent Swarm consists of numerous specialized agents, each a subclass of `BaseAgent` and responsible for a specific task. They are the "workers" who execute the puzzle-solving logic.

Key agents include:

*   **`ObserverAgent`**: The system's eyes and ears. It monitors the codebase for changes, runs tests, and gathers the raw data needed to compute E and H.
*   **`SpecOracleAgent`**: The arbiter of correctness. It evaluates the system against the formal specification (Φ) and reports any violations.
*   **`PredictorAgent`**: The risk modeler. It maintains a probabilistic risk prior (β) for each module, guiding the system away from wasteful or dangerous actions.
*   **`PlannerAgent`**: The strategist. It uses the Priority formula (P) and risk data (β) to solve a budgeted optimization problem, deciding what actions to take next.
*   **`FixerAgent`**: The hands-on tool. It receives tasks from the `Planner` and executes safe, AST-based code transformations, validating each change with targeted tests.
*   **`ConflictDetectorAgent` & `BacktrackerAgent`**: The resolution team. They identify contradictions between patches and the specification (Γ) and perform minimal, surgical rollbacks to get the system back on a productive path.
*   **`RecoveryAgent`**: The environment expert. It runs preflight checks to ensure prerequisites (packages, services, tools) are met before any code is touched.

### 2.3. The Messaging Bus (AMP)

The Agent Message Protocol (AMP) is the communication backbone of pForge. It is a typed, proof-carrying, event-driven protocol that decouples all agents.

*   **Asynchronous Communication**: Agents publish events to the bus and subscribe to the events they care about. There is no direct agent-to-agent communication.
*   **Proof-Carrying**: Every significant event (e.g., `FIX.PATCH_APPLIED`, `SPEC.CHECKED`) includes a cryptographic `ProofBundle` that contains verifiable evidence (hashes, test results, signatures) to support its claims.
*   **Idempotency**: All messages carry a unique `op_id`, allowing consumers to process messages exactly once, making the system resilient to transient failures.

### 2.4. The Storage Layer (CAS)

The Content-Addressable Store (CAS) is a foundational component that provides an immutable, auditable history of the codebase.

*   **Immutable Snapshots**: Every version of the code is stored as a content-addressed snapshot (identified by its SHA256 hash). This means that a proof tied to a specific `tree_sha` is forever verifiable against that exact version of the code.
*   **Efficient Storage & Diffing**: The CAS allows for cheap branching and diffing, enabling the `FixerAgent` to experiment in isolated sandboxes without expensive copies.
*   **Verifiable Rollbacks**: When the `BacktrackerAgent` needs to revert a change, it can do so with perfect fidelity by simply checking out a previous snapshot from the CAS.

## 3. The Solve Cycle: An End-to-End Flow

The components work together in a continuous "solve cycle."

![Solve Cycle Diagram](https://i.imgur.com/example2.png "pForge Solve Cycle Sequence Diagram")
*Figure 2: A sequence diagram illustrating a typical bug-fix cycle.*

1.  **Observation**: The `ObserverAgent` detects a failing test and publishes an `OBS.TICK` event.
2.  **State Update**: The `EfficiencyAnalyst` consumes this, updates the system state (Σ) to reflect the new bug, and computes a new, lower efficiency score (E).
3.  **Planning**: The `PlannerAgent` sees the new bug, calculates its high priority (P), and dispatches a `FixTask`.
4.  **Action & Validation**: The `FixerAgent` receives the task, generates a patch, and validates it in a sandboxed CAS snapshot with targeted tests.
5.  **Proof of Fix**: The `FixerAgent` publishes a `FIX.PATCH_APPLIED` event, including a proof bundle with the code diff, passing test results, and a new `tree_sha`.
6.  **Specification Check**: The `SpecOracleAgent` consumes the event, verifies the change against all formal constraints (Φ), and publishes a `SPEC.CHECKED` event with `sat: true`.
7.  **Convergence**: The `EfficiencyAnalyst` recomputes E, which now rises. If all other QED gates are green, the `QEDSupervisor` co-signs the final proof, and the puzzle is considered solved.

This architecture ensures that pForge operates not as a collection of ad-hoc scripts, but as a principled, self-correcting system that drives relentlessly toward a provably correct solution.
