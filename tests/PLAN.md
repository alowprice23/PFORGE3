# PLAN: `tests/` Directory

## Chunk 2 - Foundational E2E Test [x]

**Goal**: Create a basic end-to-end test for the `doctor` command.

**Status**: Completed.

## Chunk 3 - Refactor to Integration Tests & Fix Failures [~]

**Goal**: Refactor the monolithic E2E test into smaller, more focused integration tests to isolate agent functionality and debug the root cause of the test failures.

**File-by-File Plan**:

*   **`e2e/test_doctor_command.py`**:
    *   **[~]** This file is being deleted and replaced by more specific integration tests.
*   **`integration/test_observer_agent.py`**:
    *   **[x]** Created. Tests that the `ObserverAgent` can find a failing test and publish a `TESTS_FAILED` event to the in-memory bus.
*   **`integration/test_planner_agent.py`**:
    *   **[~]** Created. Tests that the `PlannerAgent` can consume a `TESTS_FAILED` event and produce a `FIX_TASK`. Currently failing due to incorrect file path inference.
*   **`integration/test_fixer_agent.py`**:
    *   **[~]** Created. Tests that the `FixerAgent` can apply a patch and verify it. Currently failing.
*   **Overall**:
    *   **[ ]** Improve error reporting in test failures to provide more context.
    *   **[ ]** Fix the underlying code in the agents until all integration tests pass.

---

*This plan is a living document and will be updated as the project evolves.*
