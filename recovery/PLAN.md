# PLAN: `recovery/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `recovery/` directory is the foundation of pForge's operational stability and awareness. Its purpose is to detect, diagnose, and automatically remediate failures in the execution environment, ensuring that the system never wastes time, resources, or analytical cycles trying to "fix code" when the actual problem lies with a prerequisite. It embodies the core principle: **"Don't debug the application when the world is broken."**

**Scope of Ownership**:

*   **Preflight Check Engine (`preflight.py`)**: It owns the orchestrator for the preflight process, which systematically verifies all environmental prerequisites before allowing semantic analysis to begin. This includes managing the dependency lattice of checks and repairs.
*   **Environmental Detectors (`detectors/`)**: It owns the complete suite of specific, targeted functions that probe the environment to detect misconfigurations or failures. This includes checking runtime versions, package integrity, service availability, port usage, and more.
*   **Remediation Actions (`actions/`)**: It owns the corresponding set of idempotent, proof-carrying actions that can repair a broken environment. This includes relocking environments, resolving packages, starting fallback services, and stabilizing non-deterministic test conditions.
*   **Prerequisite Constraint Management**: It is responsible for turning implicit assumptions about the environment into explicit, verifiable constraints (`φ_π`) that are integrated into the main specification (Φ).

**Explicitly Not in Scope**:

*   **Semantic Code Analysis**: This directory does not analyze the logic, style, or structure of the target codebase. That is the responsibility of the `agents/` and `tools/` directories.
*   **General Task Planning**: It does not perform general-purpose planning. Its planning is limited to creating a dependency-ordered sequence of remediation actions. The main `PlannerAgent` handles all other planning.
*   **User-Facing Interfaces**: While the results of its actions are surfaced in the UI and CLI, it does not own those interface components.

---

## 2. File-by-File Blueprints

The directory is organized into a main engine (`preflight.py`) and two subdirectories for `detectors/` and `actions/`.

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `recovery/` directory as a Python package.

### 2.2. `preflight.py`

*   **Responsibilities**:
    *   To orchestrate the end-to-end preflight check.
    *   To define the prerequisite lattice (μ), specifying the dependencies between checks (e.g., must have a valid runtime before checking packages).
    *   To run all detectors, collect their `CheckResult` objects, and identify the unsat core of failing, blocking prerequisites.
    *   To create and execute a plan of remediation actions from the `actions/` directory, respecting the dependency order.
    *   To continue this detect-remediate loop until a fixpoint is reached (i.e., no more blocking prerequisites are failing) or a budget is exhausted.
*   **Data Models**: `Prerequisite(id: str, detector: Callable, action: Callable, dependencies: set[str])`.
*   **Algorithms**:
    *   **Fixpoint Iteration**: A `while` loop that continues as long as the set of satisfied prerequisites is growing.
    *   **Topological Sort**: Used on the prerequisite lattice to generate a valid execution order for remediation actions.
*   **Tests**: A `test_preflight.py` will use mock detectors and actions to verify that the engine correctly identifies failures, plans a valid sequence of repairs, and reaches a stable fixpoint.

### 2.3. `detectors/` Subdirectory

This directory contains the individual sensor functions. Each module is focused on a specific category of environmental checks.

*   **`__init__.py`**: Exports all detector functions.
*   **`runtime_versions.py`**: Contains `check_python_version()`, `check_node_version()`, etc. They compare the output of `python --version` with ranges specified in `pyproject.toml` or other config files.
*   **`packages.py`**: Contains `check_pip_dependencies()` (runs `pip check`) and `check_npm_dependencies()` (runs `npm ci --dry-run`).
*   **`services.py`**: Contains `check_redis_connection()`, `check_postgres_connection()`. They attempt a simple connection and return the health status.
*   **`ports.py`**: Contains `check_port_in_use(port: int)`. It attempts to bind to a port to see if it's free.
*   **`secrets.py`**: Contains `check_required_secrets_present()`. It checks `os.environ` for the *existence* of keys like `OPENAI_API_KEY`, but **never** reads or logs their values.
*   **`time_tz.py`**: Contains `check_timezone()` and `detect_time_flakiness()` by analyzing test report timings.
*   **`data_migrations.py`**: Contains `check_db_schema_version()` which connects to the database and checks a `schema_migrations` table.
*   **`tooling_drift.py`**: Contains `check_tool_versions()` which compares the output of `mypy --version`, `pytest --version`, etc., against the locked versions in `requirements.txt`.

### 2.4. `actions/` Subdirectory

This directory contains the corresponding idempotent remediation functions. Each action performs a single, verifiable fix.

*   **`__init__.py`**: Exports all action functions.
*   **`env_relock.py`**: Contains `recompute_venv_lock()`. It freezes dependencies and tool versions into a new `venv_lock_sha`.
*   **`pkg_resolve.py`**: Contains `install_pip_packages()`, `install_npm_packages()`. They run `pip install` or `npm ci` in the sandbox.
*   **`service_boot.py`**: Contains `start_fakeredis()`. It starts an in-process `fakeredis` server on a free port.
*   **`port_reassign.py`**: Contains `find_free_port()` and `update_config_port()`.
*   **`clock_freeze.py`**: Contains `inject_time_freeze_fixture()`, which can modify a `pytest` conftest to inject a time-mocking fixture.
*   **`tz_set.py`**: Contains `set_utc_for_tests()`, which wraps a command with the `TZ=UTC` environment variable.
*   **`migrate_seed.py`**: Contains `run_db_migrations()`, which uses a tool like `alembic` to upgrade a sandboxed database.

---

## 3. Math & Guarantees (from README)

This directory provides the mathematical guarantee of a **stable foundation**.

*   **Prerequisite Lattice and Fixpoint (μ)**: The `preflight.py` engine's core algorithm is a direct implementation of the fixpoint calculation `μ = lfp(F)`. This guarantees that the process of repairing the environment is deterministic, ordered, and will terminate in a stable state.
*   **Explicit Constraints (φ_π)**: By turning implicit environmental assumptions into explicit, blocking constraints (`φ_π`), this directory ensures that the system's correctness proofs (`S(Σ,t) = 1`) are not built on a faulty foundation. A proof is only valid if its prerequisite constraints are also met.

The guarantee is that pForge's semantic analysis will only ever run on an environment that is verifiably correct, preventing entire classes of "phantom" bugs.

---

## 4. Routing & Awareness

The `recovery/` directory provides **environmental awareness**. Before this directory's preflight check, the system is "blind" to the state of the world it runs in. After the preflight check, the system is fully aware of:

*   Which runtimes and tools are available and their versions.
*   The integrity of its package dependencies.
*   The health of its required services.
*   Any potential resource conflicts (like ports).
*   The stability of its testing environment (time, timezone).

This awareness is passed to the `Planner` and `QEDSupervisor`, which will refuse to proceed with semantic work until the `RecoveryAgent` has signaled that all blocking prerequisite constraints are satisfied.

---

## 5. Token & Budget Hygiene

This directory is a major contributor to budget hygiene. By catching and fixing environmental issues that would cause LLM-driven agents to fail or waste cycles, it prevents the system from spending expensive tokens on problems that cannot be solved with code changes. Every failed LLM call that is avoided is a direct saving.

---

## 6. Operational Flows

*   **Preflight Check on Startup**:
    1.  The `Orchestrator` starts.
    2.  It dispatches the `RecoveryAgent` to run a preflight check.
    3.  `preflight.py` runs all detectors. Let's say `packages.py` detects a missing dependency.
    4.  The preflight engine identifies `pkg_resolve.py` as the required remediation action.
    5.  It executes the action, which runs `pip install`.
    6.  The action succeeds and emits a `RECOVERY.PKG_RESOLVED` event with a proof (the `pip check` exit code).
    7.  The engine re-runs the detectors, which now all pass.
    8.  The `RecoveryAgent` signals that the preflight is complete and successful.
    9.  The `Orchestrator` now allows the `Planner` to begin scheduling semantic work.

---

## 7. Testing & Backtests

*   **Unit Tests**: Each detector and action will be unit tested with extensive mocking of the `subprocess` and `os` modules to simulate different environmental conditions. For example, `test_ports.py` will mock `socket.bind` to throw an `EADDRINUSE` error and verify the detector catches it.
*   **Integration Tests**: `recovery_preflight_test.py` will test the `preflight.py` engine's ability to correctly sequence a multi-step recovery (e.g., it must detect a runtime mismatch *before* trying to check packages that depend on it).
*   **Backtesting**: The `RECOVERY.*` proofs in the AMP log are fully backtestable. The `verifier` can re-run the detectors on the same code snapshot and assert that they produce the same `CheckResult`. It can also verify the proofs from the remediation actions (e.g., checking that the `venv_lock_sha` in the proof matches the re-computed hash).

---

## 8. Security & Policy

This directory is a critical security component.

*   **Hardening the Environment**: The actions in this directory work to create a hardened, reproducible environment, which reduces the attack surface.
*   **Capability Gating**: Remediation actions that modify the environment (e.g., `pkg_resolve.py`) are privileged and must be executed with a valid capability token.
*   **Dependency Security**: `packages.py` can be extended to check for known vulnerabilities in dependencies (e.g., using `pip-audit`), turning security advisories into blocking prerequisite constraints.
*   **Secret Handling**: The `secrets.py` detector ensures the system fails closed if secrets are not available, preventing it from running in an insecure configuration.

---

## 9. Readme Cross-Reference

This directory addresses the foundational, often unstated, requirements of the puzzle-solving analogy in the `README.md`.

| Recovery Component | README.md Puzzle Analogy |
| :--- | :--- |
| **Preflight Check** | Before starting a puzzle, you make sure you're at a sturdy table, the lighting is good, you have all the pieces from the box, and you don't have pieces from another puzzle mixed in. |
| **Detectors** | The act of noticing "the table is wobbly" or "I'm missing all the edge pieces." |
| **Actions** | The act of fixing the wobbly table leg or finding the missing bag of edge pieces before you begin. |

The `recovery/` directory ensures that pForge never gets frustrated trying to solve a puzzle with a wobbly table in the dark. It fixes the environment first, so all subsequent effort can be focused entirely on the puzzle itself.
