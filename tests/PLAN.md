# PLAN: `tests/` Directory

## 1. Directory Purpose & Scope

**Purpose**: To ensure the correctness, reliability, and robustness of the pForge system through a comprehensive, multi-layered automated testing strategy. This directory is the canonical source of truth for the system's expected behavior. It contains the code that programmatically verifies all other components, from individual mathematical functions to the full end-to-end user workflow, guaranteeing that the system performs as designed and that new changes do not introduce regressions.

**Scope of Ownership**:

*   **Unit Tests (`unit/`)**: It owns the tests for individual functions and classes in complete isolation, with all external dependencies mocked.
*   **Integration Tests (`integration/`)**: It owns the tests that verify the interaction and contracts between two or more internal components of the system, often using lightweight, in-memory fakes for external services like Redis.
*   **End-to-End Tests (`e2e/`)**: It owns the tests that verify the entire system running as a whole, interacting with it only through its public interfaces (the API and the CLI).
*   **Test Fixtures and Helpers**: It owns any shared test fixtures (e.g., `conftest.py`), test data generators, and helper functions used across the test suite.

**Explicitly Not in Scope**:

*   **Application Source Code**: This directory contains only test code. All application logic resides in the other source directories.
*   **Backtesting Verifiers**: It does not contain the `verifiers/` scripts. The `tests/` directory is for automated, pre-commit-style testing, while the `verifiers/` are for post-hoc analysis and auditing of historical runs.
*   **The Test Runner Itself**: It does not own the test runner (e.g., `pytest`). It contains the tests that are executed by the runner.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `tests/` directory as a Python package, allowing `pytest` to discover the test modules within its subdirectories.

### 2.2. `unit/` Subdirectory

This directory contains fast-running tests that check components in isolation.

*   **`test_efficiency_engine.py`**: Verifies the mathematical correctness of the `E` and `H` formula implementations in `orchestrator/efficiency_engine.py` with known inputs.
*   **`test_entropy_metric.py`**: Contains focused tests for the individual components of the entropy `H` calculation.
*   **`test_selection_reverse_closure.py`**: Tests the graph traversal algorithm in `validation/dep_graph.py` with mock graphs.
*   **`test_coverage_selection.py`**: Tests the test-selection logic in `validation/selection.py` with mock coverage maps.
*   **`test_delta_typecheck.py`**: Tests the file selection logic for incremental typechecking in `validation/types.py`.
*   **`test_refine_policy.py`**: Tests the `FixerAgent`'s internal logic for its bounded refinement loop.
*   **`test_capabilities_and_redaction.py`**: Contains critical security unit tests for the functions in `proof/capabilities.py` and `proof/redaction.py`, verifying token validation and secret scrubbing.

### 2.3. `integration/` Subdirectory

This directory contains tests that verify the contracts between modules.

*   **`onboarding_flow_test.py`**: Tests the flow of onboarding a new repository, verifying that `sandbox/fs_manager.py` correctly interacts with `storage/cas.py`.
*   **`solve_cycle_test.py`**: Tests the primary agent loop, simulating an `OBS.TICK` event and verifying that it correctly flows through the `PlannerAgent`, `FixerAgent`, and `SpecOracleAgent`, resulting in a valid `FIX.PATCH_APPLIED` event.
*   **`merge_conflict_test.py`**: Tests the conflict resolution flow, simulating a `SPEC.CHECKED` failure and verifying that the `ConflictDetector` and `Backtracker` agents correctly collaborate to resolve it.
*   **`targeted_then_full_test.py`**: Tests the "fast but honest" validation policy. It will simulate a patch where targeted tests pass but a full audit fails, and assert that the `QEDSupervisor` does not fire until the full audit passes.
*   **`recovery_preflight_test.py`**: Tests the `recovery/preflight.py` engine with mock detectors and actions to ensure it correctly plans and executes a remediation sequence.
*   **`throttle_control_test.py`**: Tests the PI controller in the `Orchestrator` by feeding it simulated latency data and asserting that it correctly adjusts the agent concurrency.

### 2.4. `e2e/` Subdirectory

This directory contains tests that treat the entire application as a black box.

*   **`smoke_local_no_docker.py`**: The most basic e2e test. It executes the `scripts/local_boot.sh` script to start the server, then makes an HTTP request to the `/metrics` endpoint and asserts that it gets a 200 OK response. This verifies that the application can start without crashing.
*   **`qed_gate_end_to_end.py`**: The most comprehensive test. It will programmatically:
    1.  Start the pForge server.
    2.  Use the `/files/onboard` API to submit the `demo_buggy/` project.
    3.  Use the `/chat/nl` API to send the command "doctor this project".
    4.  Poll the `/chat/events` stream until it sees a `QED.EMITTED` event.
    5.  Download the final, fixed files and assert that the bugs have been corrected.

---

## 3. Math & Guarantees (from README)

This directory provides the ultimate guarantee of **Correctness and Reliability**. It is the practical, automated verification of the mathematical guarantees made by all other components.

*   `test_efficiency_engine.py` directly asserts that the code implements the `E` formula correctly.
*   The integration tests assert that the system behaves according to the logic of the puzzle-solving framework (e.g., that conflicts are resolved, that plans are executed).
*   The e2e tests provide the final guarantee that the sum of all the mathematical parts results in a system that can actually solve a real problem.

---

## 4. Routing & Awareness

The test suite is organized to be aware of the application's structure, with `unit/`, `integration/`, and `e2e/` directories mirroring the different levels of abstraction. The tests themselves must be aware of the system's event-driven nature, often requiring them to publish a message to the bus and then poll for an expected response.

---

## 5. Token & Budget Hygiene

The test suite must be designed to be budget-conscious.
*   **LLM Marking**: All tests that would trigger a real LLM call (primarily e2e tests) will be marked with `@pytest.mark.llm`. The CI will be configured to skip these tests by default (`pytest -m "not llm"`). They will only be run in a special, budget-approved CI job.
*   **Mocking**: The vast majority of unit and integration tests will use mock LLM clients that return canned responses, consuming no tokens.

---

## 6. Operational Flows

*   **Continuous Integration (CI) Flow**:
    1.  A developer pushes a commit.
    2.  The GitHub Actions workflow defined in `devops/ci/` is triggered.
    3.  It runs the `scripts/run_tests.sh` script.
    4.  This script executes `pytest`, which discovers and runs all tests in this directory.
    5.  It also runs the frontend tests (`npm test`).
    6.  The developer can only merge their pull request if all tests pass.

---

## 7. Testing & Backtests

This entire directory is dedicated to testing. It is the implementation of the testing strategy.

---

## 8. Security & Policy

The test suite is a critical part of the security development lifecycle.
*   **Security Tests**: `test_capabilities_and_redaction.py` and other security-focused tests directly verify that the system's security controls are working as intended.
*   **Secure Test Practices**: The test suite itself must be secure. It will never contain hardcoded secrets or API keys. All test-specific secrets will be loaded from the environment, just like in the main application.

---

## 9. Readme Cross-Reference

The `tests/` directory is the automated, rigorous process of checking the solution to the puzzle described in the `README.md`.

| Test Suite | README.md Puzzle Analogy |
| :--- | :--- |
| **Unit Tests** | Checking a single puzzle piece to make sure it's not damaged and has the shape printed on the box. |
| **Integration Tests** | Taking two or three pieces and confirming that they "click" together perfectly. |
| **End-to-End Tests** | Taking the fully assembled puzzle, carefully lifting it off the table, and shaking it to make sure that not a single piece falls out, proving that the entire structure is solid. |

This directory provides the confidence that the pForge system is not just theoretically correct, but practically robust.
