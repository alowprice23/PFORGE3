# PLAN: `tests/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `tests/` directory contains the complete test suite for the pForge system. It is responsible for verifying the correctness, robustness, and performance of every component in the system, from the lowest-level utility functions to the end-to-end behavior of the agentic swarm. This directory is what gives us the confidence to refactor and extend the system without introducing regressions.

**Scope of Ownership**:

*   **Unit Tests (`unit/`)**: It owns the unit tests for all the individual modules and classes in the system. These tests are fast, isolated, and do not have any external dependencies.
*   **Integration Tests (`integration/`)**: It owns the integration tests that verify the interactions between different components of the system. These tests may require a running Redis server or other local services.
*   **End-to-End Tests (`e2e/`)**: It owns the end-to-end tests that verify the behavior of the entire system from the user's perspective. These tests typically involve running the CLI or interacting with the web UI to perform a complete workflow.

**Explicitly Not in Scope**:

*   **Application Code**: This directory contains only test code. The application code resides in the `pforge/` directory.
*   **Test Data**: The data used by the tests is stored in the `data/` directory.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `tests/` directory as a Python package.

### 2.2. `unit/` Subdirectory

This directory contains the unit tests for the individual modules.

*   **`test_efficiency_engine.py` [ ]**: Tests the `E_intelligent` formula with a variety of inputs to ensure that it behaves as expected.
*   **`test_entropy_metric.py` [ ]**: Tests the entropy calculation for style, structure, and process.
*   **`test_selection_reverse_closure.py` [ ]**: Tests the reverse-dependency closure algorithm in `validation/selection.py`.
*   **`test_coverage_selection.py` [ ]**: Tests the targeted test selection logic.
*   **`test_delta_typecheck.py` [ ]**: Tests the delta type checking logic.
*   **`test_refine_policy.py` [ ]**: Tests the refinement policy in the `FixerAgent`.
*   **`test_capabilities_and_redaction.py` [ ]**: Tests the capability token and data redaction logic.

### 2.3. `integration/` Subdirectory

This directory contains the integration tests for the system.

*   **`onboarding_flow_test.py` [ ]**: Tests the project onboarding flow, from copying the repo into the sandbox to the first `OBS.TICK` event.
*   **`solve_cycle_test.py` [ ]**: Tests the main solve cycle, from bug detection to patch application and verification.
*   **`merge_conflict_test.py` [ ]**: Tests the conflict detection and resolution flow.
*   **`targeted_then_full_test.py` [ ]**: Tests that the system correctly runs the targeted tests first and then escalates to the full suite before QED.
*   **`recovery_preflight_test.py` [ ]**: Tests the preflight checks and remediation actions.
*   **`throttle_control_test.py` [ ]**: Tests the metrics-driven throttling controller.

### 2.4. `e2e/` Subdirectory

This directory contains the end-to-end tests for the system.

*   **`smoke_local_no_docker.py` [ ]**: A simple smoke test that runs the system in local-only mode and verifies that it can start up and respond to a basic status query.
*   **`qed_gate_end_to_end.py` [ ]**: A full end-to-end test that runs the system on a buggy project and verifies that it can successfully repair the code and reach a QED state.

---

## 3. Math & Guarantees (from README)

The `tests/` directory is where the mathematical guarantees of the system are verified. The unit tests for the `efficiency_engine` and `priority` modules directly test the implementation of the core mathematical formulas. The integration and end-to-end tests verify that the system as a whole behaves in a way that is consistent with the mathematical model, e.g., that the efficiency score `E` actually increases as the system fixes bugs. This directory is what makes the system's claims about its mathematical rigor **falsifiable** and **testable**.
