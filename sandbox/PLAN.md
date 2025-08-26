# PLAN: `sandbox/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `sandbox/` directory provides a safe, isolated, and stateful filesystem environment where agents can analyze and modify code. Its primary purpose is to abstract the complexities of file management and versioning, allowing agents to operate on a "worktree" without affecting the user's original source repository or the host system. It is the tangible implementation of the "puzzle board" where all work is performed.

**Scope of Ownership**:

*   **Sandbox Lifecycle Management (`fs_manager.py`)**: It owns the high-level functions for managing the sandbox lifecycle. This includes creating a new sandbox by onboarding a source repository, creating immutable, content-addressed snapshots of the sandbox's state, checking out any snapshot into a clean, writable worktree, and handling rollbacks.
*   **State Comparison (`diff_utils.py`)**: It is responsible for generating structured and human-readable differences between any two snapshots, providing a clear record of what changed.
*   **Synchronization (`merge_back.py`)**: It owns the logic for safely merging the finalized, proven changes from the sandbox back into the user's original source repository, complete with conflict detection.
*   **Path Safety Policy (`path_policy.py`)**: It owns and enforces the critical security policy that ensures no file operation can escape the designated sandbox directory.

**Explicitly Not in Scope**:

*   **Low-Level Storage**: It does not implement the underlying Content-Addressable Store (CAS). It is a client of `storage/cas.py`, which handles the storage of file content as hashed blobs.
*   **Agent Logic**: It contains no agent-specific logic. Agents are the *clients* of the sandbox.
*   **The Filesystem Itself**: It does not implement filesystem operations; it is a manager that uses standard libraries (`os`, `shutil`) and tools (`git`) to interact with the filesystem.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `sandbox/` directory as a Python package and re-export the primary functions from `fs_manager.py` for convenient access.
*   **Interfaces**: Provides the main entry points for the sandbox system to the rest of pForge.

### 2.2. `fs_manager.py`

*   **Responsibilities**: To manage the core lifecycle of sandbox states.
    *   `onboard_repo(source_path: str) -> str`: Takes a path to a user's repository, copies all its content into the CAS via `storage/cas.py`, creates an initial tree and commit object, and returns the initial commit SHA.
    *   `create_snapshot(worktree_path: str, parent_commit_sha: str, msg: str) -> str`: Takes the path to a modified worktree, creates a new CAS snapshot (tree and commit objects) representing its current state, and returns the new commit SHA.
    *   `checkout_snapshot(commit_sha: str, target_worktree_path: str) -> None`: "Hydrates" a specified worktree directory with the exact file contents of a given snapshot, ensuring a clean state for an agent to work in.
    *   `rollback(commit_sha: str, worktree_path: str) -> None`: A convenience wrapper around `checkout_snapshot` to revert a worktree to a previous state.
*   **Data Models**: Interacts with the tree and commit object models, which are dictionaries conforming to a schema (e.g., `{"tree": "sha...", "parent": "sha...", "message": "..."}`).
*   **Tests**: A `test_fs_manager.py` will test the full lifecycle: onboarding, creating a snapshot, modifying a file, creating a second snapshot, and then rolling back to the first, asserting the file contents are correct at each stage.

### 2.3. `diff_utils.py`

*   **Responsibilities**: To provide functions for comparing two states of the sandbox.
    *   `diff_snapshots(commit_a_sha: str, commit_b_sha: str) -> dict`: Loads the tree objects for both commits from the CAS and computes a structured diff, returning a dictionary like `{"added": [...], "removed": [...], "changed": [...]}`. For changed files, it includes the before and after blob hashes.
    *   `format_diff_for_display(diff: dict) -> str`: Takes a structured diff object and produces a human-readable, colored, unified diff string suitable for logging or display in the UI/CLI.
*   **Data Models**: The structured diff dictionary.
*   **Tests**: `test_diff_utils.py` will create two distinct snapshots and assert that `diff_snapshots` correctly identifies all added, removed, and modified files.

### 2.4. `merge_back.py`

*   **Responsibilities**: To handle the final, critical step of applying the sandbox changes to the user's original repository.
    *   `execute_merge(source_repo_path: str, final_commit_sha: str) -> MergeResult`: This function will use a safe `git`-based strategy to merge the changes. A common approach is to add the sandbox's CAS as a temporary git remote, fetch the final commit, and perform a merge with conflict detection.
*   **Data Models**: `MergeResult(success: bool, conflict: bool, message: str)`.
*   **Algorithms**: Git merge strategies. It must handle merge conflicts gracefully, aborting the merge and reporting the conflict rather than leaving the user's repository in a broken state.
*   **Tests**: `test_merge_back.py` will use two temporary git repositories to simulate the source and sandbox, testing both a successful merge and a merge that results in a conflict, asserting the final state is correct in both cases.

### 2.5. `path_policy.py`

*   **Responsibilities**: To be the security guard for all filesystem operations.
    *   `is_path_safe(path_to_check: str, sandbox_root: str) -> bool`: This is the core function. It resolves the absolute path of `path_to_check` and verifies that it is a subdirectory of `sandbox_root`. It must correctly handle symlinks, `..` traversal, and other common escape techniques.
*   **Algorithms**: Path resolution and prefix checking. It will use `os.path.realpath` to resolve symlinks and then perform a string or path object comparison.
*   **Security**: This is one of the most critical security components in the entire system. A flaw here could allow an agent to read or write arbitrary files on the host system.
*   **Tests**: `test_path_policy.py` will have an extensive suite of test cases, including valid paths, malicious paths (`/etc/passwd`, `../secrets.txt`), paths with symlinks pointing outside the sandbox, and paths with unusual character encodings.

---

## 3. Math & Guarantees (from README)

The `sandbox/` directory provides the foundational guarantee of **State Integrity and Isolation**.

*   **Immutable State (`Σ`)**: By building on the Content-Addressable Store, the `fs_manager.py` ensures that every snapshot is an immutable, verifiable representation of the system's code state (C). The `tree_sha` is a mathematical fingerprint that guarantees the integrity of this state. This is the bedrock that allows all other proofs (test results, constraint checks) to be meaningful, as they are anchored to a state that cannot be undetectably modified.
*   **Isolation**: The `path_policy.py` provides the guarantee that all agent operations are confined within the sandbox. This prevents the system's internal operations from having unintended side effects on the user's system, which is a prerequisite for any trustworthy autonomous system.

---

## 4. Routing & Awareness

This directory provides **State Awareness**. The snapshot SHAs generated by `fs_manager.py` are the canonical identifiers for the state `Σ` that are passed around in AMP events. When any agent receives an event, it can use the `snap_sha` and the `checkout_snapshot` function to materialize the exact same filesystem state that the producing agent was working with. This eliminates all ambiguity about the context of an operation and is fundamental to the system's deterministic and auditable nature.

---

## 5. Token & Budget Hygiene

This directory's operations are local and do not consume LLM tokens. It has no direct impact on budget hygiene.

---

## 6. Operational Flows

*   **A Fixer Agent's Full Workflow**:
    1.  The `FixerAgent` receives a `FixTask` AMP event, which includes a `snap_sha` for the "before" state.
    2.  It calls `fs_manager.checkout_snapshot(snap_sha, ...)` to create a clean worktree.
    3.  It modifies the files in the worktree.
    4.  It calls `fs_manager.create_snapshot(...)` to get a new "after" `snap_sha`.
    5.  It calls `diff_utils.diff_snapshots(...)` to get the diff between the before and after states.
    6.  It includes the new `snap_sha` and the diff in the proof bundle of its `FIX.PATCH_APPLIED` event.
*   **Final Merge Flow**:
    1.  The `QEDSupervisor` emits the final `QED.EMITTED` event, which contains the `snap_sha` of the proven, final state.
    2.  The `Orchestrator` or a dedicated merge agent receives this event.
    3.  It calls `merge_back.execute_merge(source_repo_path, final_snap_sha)`.
    4.  The function performs the git merge and reports the result.

---

## 7. Testing & Backtests

*   **Unit Tests**: Each module will have focused unit tests as described in the blueprints, using mock filesystems and a mock CAS.
*   **Integration Tests**: The `onboarding_flow_test.py` will be a key integration test, verifying that `fs_manager.py` can correctly interact with `storage/cas.py` to create an initial snapshot.
*   **Backtesting**: The `verifier.py` is a primary client of this directory. To verify any historical proof, its first action is to call `checkout_snapshot` to get the exact code that the proof pertains to. The integrity of the sandbox and snapshotting mechanism is therefore fundamental to the entire backtesting and verification process.

---

## 8. Security & Policy

This directory is a **primary security boundary**.

*   **Sandboxing (`path_policy.py`)**: This is the most critical security function. It must be rigorously tested to prevent any form of path traversal or symlink escape that could allow an agent to access the host filesystem.
*   **Merge Safety (`merge_back.py`)**: The merge process must be safe, detecting conflicts and aborting cleanly rather than leaving the user's repository in a broken or partially merged state. Using `git`'s mature merging capabilities is the key to this safety.

---

## 9. Readme Cross-Reference

The `sandbox/` directory is the physical implementation of the "puzzle board" from the `README.md`'s puzzle-solving framework.

| Sandbox Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `fs_manager.onboard_repo` | The act of taking the puzzle pieces out of the box and spreading them out on the board for the first time. |
| `fs_manager.create_snapshot` | Taking a photograph of the current state of the puzzle on the board to record your progress. The `tree_sha` is the unique identifier for that photograph. |
| `fs_manager.rollback` | Looking at an old photograph and reverting the pieces on the board to match it exactly, undoing a mistake. |
| `path_policy.py` | The raised wooden edge of the puzzle board, which ensures that no pieces can accidentally fall off onto the floor or get lost. |

This directory provides the stable, isolated, and versioned workspace that allows the agents to solve the puzzle without chaos or external interference.
