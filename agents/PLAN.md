# PLAN: `agents/` Directory

## Chunk 2 - Foundational Agent Workflow [x]

**Goal**: Establish the basic end-to-end `Observer -> Planner -> Fixer` agent flow.

**Status**: Completed.

## Chunk 3 - Test-Driven Repair and Verification Loop [~]

**Goal**: Evolve the agent workflow into a genuine, test-driven repair system that runs entirely locally.

**File-by-File Plan**:

*   **`base_agent.py`**:
    *   **[x]** Refactor `send_amp_event` to use the new `InMemoryBus`.
*   **`observer_agent.py`**:
    *   **[x]** Modify `on_tick` to run the project's test suite using `pforge.validation.test_runner.run_tests()`.
    *   **[x]** If the test run fails, publish a `TESTS_FAILED` event to the in-memory bus.
*   **`planner_agent.py`**:
    *   **[x]** Update the agent to listen for `TESTS_FAILED` events from the in-memory bus.
    *   **[ ]** Correctly infer the source file path from the test file path.
*   **`fixer_agent.py`**:
    *   **[x]** After applying a patch, immediately trigger a verification step by re-running the *specific* failing test.
    *   **[x]** Update the `ProofBundle` with the real results of the verification test run.
*   **Overall**:
    *   **[x]** Remove all dependencies on `redis` and `redis_stream.py`.

---

*This plan is a living document and will be updated as the project evolves.*
