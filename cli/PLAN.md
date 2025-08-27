# PLAN: `cli/` Directory

## Chunk 2 - Foundational `doctor` Command [x]

**Goal**: Create the initial `pforge doctor run` command.

**Status**: Completed.

## Chunk 3 - Local-Only Agent Orchestration [~]

**Goal**: Refactor the `doctor` command to orchestrate the agent workflow entirely in-memory, without Redis or a server.

**File-by-File Plan**:

*   **`skills/doctor.py`**:
    *   **[x]** Remove all Redis-related code (`redis`, `fakeredis`).
    *   **[x]** Instantiate and pass the new `InMemoryBus` to the agents.
    *   **[x]** Update the event waiting logic to use the `InMemoryBus` queue instead of `xread` or `pubsub`.
*   **E2E Test (`pforge/tests/e2e/test_doctor_command.py`)**:
    *   **[~]** This test is being refactored into smaller integration tests to better isolate component functionality. The final E2E test will be simplified to just run the `doctor` command and assert the final outcome.

---

*This plan is a living document and will be updated as the project evolves.*
