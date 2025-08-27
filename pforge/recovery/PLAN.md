# PLAN: `recovery/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `recovery/` directory implements the "Don't Fix Code When the World Is Broken" principle. It is responsible for detecting and remediating prerequisite failures—problems with the environment, dependencies, or local services that would otherwise cause the system to waste time on fruitless debugging attempts. This directory ensures that pForge only attempts to fix semantic code issues when it is operating in a stable, predictable, and correct environment.

**Scope of Ownership**:

*   **Preflight Engine (`preflight.py`)**: It owns the main preflight engine that orchestrates the detection and remediation of all prerequisite issues. It implements the fixpoint algorithm that ensures all environmental dependencies are met before proceeding.
*   **Detectors (`detectors/`)**: It owns the collection of specialized detectors that identify specific prerequisite failures, such as incorrect runtime versions, broken package dependencies, or unavailable services.
*   **Remediation Actions (`actions/`)**: It owns the set of concrete, proof-carrying actions that can be taken to remediate prerequisite failures, such as re-locking the environment, installing packages, or starting a fake Redis server.

**Explicitly Not in Scope**:

*   **Semantic Code Analysis**: This directory is not concerned with the logic of the application code. It only deals with the environment in which the code runs.
*   **Agent Logic**: The `RecoveryAgent` is the client of the services provided by this directory, but its logic resides in the `agents/` directory.
*   **Configuration**: It consumes configuration (e.g., expected runtime versions), but does not own the config files.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `recovery/` directory as a Python package.

### 2.2. `preflight.py` [ ]

*   **Responsibilities**: To implement the main preflight engine.
    *   It maintains the prerequisite lattice (μ) and the set of all prerequisite constraints (Φ_π).
    *   On each run, it invokes all detectors to check the current state of the environment.
    *   If any blocking prerequisites are not met, it computes an unsat core and dispatches the appropriate remediation actions.
    *   It continues this loop until a fixpoint is reached (i.e., all prerequisites are satisfied, or no further progress can be made).
*   **Algorithms**: Implements the `μ = lfp(F)` fixpoint algorithm.
*   **Interfaces**: Used by the `RecoveryAgent` to run the preflight checks.

### 2.3. `detectors/` Subdirectory

This directory contains the individual detectors for specific prerequisite failures. Each detector is a simple function that returns a `CheckResult` object.

*   **`runtime_versions.py` [ ]**: Checks that the versions of Python, Node, etc., match the ranges specified in the project's configuration.
*   **`packages.py` [ ]**: Runs `pip check` and `npm ci --dry-run` to verify the integrity of the package dependencies.
*   **`services.py` [ ]**: Probes for the availability of required services like Redis and falls back to checking for the `fakeredis` library if the real service is not available.
*   **`ports.py` [ ]**: Checks for port collisions.
*   **`secrets.py` [ ]**: Checks for the presence of required API keys in the environment.
*   **`time_tz.py` [ ]**: Detects non-deterministic time and timezone configurations.
*   **`data_migrations.py` [ ]**: Checks for database schema drift.
*   **`tooling_drift.py` [ ]**: Checks that the versions of the development tools (mypy, pytest, etc.) are correct.

### 2.4. `actions/` Subdirectory

This directory contains the remediation actions for specific prerequisite failures. Each action is a function that performs a specific task and returns a proof of its execution.

*   **`env_relock.py` [ ]**: Re-locks the environment by re-generating the lock files and computing the `venv_lock_sha`.
*   **`pkg_resolve.py` [ ]**: Installs or repairs package dependencies using the local cache.
*   **`service_boot.py` [ ]**: Starts a fake Redis server or other embedded services.
*   **`port_reassign.py` [ ]**: Finds a free port and updates the configuration.
*   **`clock_freeze.py` [ ]**: Injects a deterministic clock into the test fixtures.
*   **`tz_set.py` [ ]**: Sets the timezone to UTC for the test run.
*   **`migrate_seed.py` [ ]**: Runs database migrations and seeds the database.

---

## 3. Math & Guarantees (from README)

The `recovery/` directory is the implementation of the prerequisite lattice and the fixpoint algorithm that ensures the stability of the environment. The guarantees of this directory are:

*   **Soundness**: The system will not attempt to fix semantic code issues until all blocking prerequisites are met.
*   **Idempotency**: All remediation actions are idempotent and can be safely re-run.
*   **Auditability**: Every remediation action is proof-carrying, providing a verifiable record of the changes made to the environment.

This directory is what prevents the system from wasting time and resources on problems that are not actually in the code.
