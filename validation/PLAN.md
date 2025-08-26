# PLAN: `validation/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `validation/` directory provides the essential machinery for fast, targeted, and provably sound validation of code changes. It is the implementation of pForge's "fast but honest" philosophy, enabling the system to make rapid progress by intelligently selecting what to verify, without sacrificing the rigor required for a final, trustworthy solution. Its primary role is to answer the question: "Given this specific change, what is the smallest set of checks we can run to be reasonably confident it didn't break anything?"

**Scope of Ownership**:

*   **Targeted Test Selection (`selection.py`)**: It owns the core algorithm for selecting a minimal-but-sound subset of tests to run in response to a code change. This logic is a critical performance optimization.
*   **Delta Typechecking (`types.py`)**: It owns the logic for running the typechecker (e.g., `mypy`) on only the subset of files affected by a change, providing another significant speedup.
*   **Test Execution (`test_runner.py`)**: It owns the robust wrapper for invoking the underlying test framework (e.g., `pytest`). This includes capturing results, parsing reports, and ensuring execution is secure and sandboxed.
*   **Index Management (`coverage_index.py`, `dep_graph.py`)**: It is responsible for creating, maintaining, and checking the freshness of the data indices that the selection algorithms depend on: the test-to-file coverage map (K) and the module dependency graph (G).

**Explicitly Not in Scope**:

*   **Decision to Validate**: This directory does not decide *when* to run validation. That decision is made by agents, primarily the `FixerAgent` after applying a patch.
*   **Interpretation of Results**: It does not interpret the meaning of a test failure or a type error in the context of the system's goals. It simply reports the raw results. The `ObserverAgent`, `EfficiencyAnalyst`, and `PlannerAgent` are responsible for that interpretation.
*   **The Tests Themselves**: It does not contain the actual test files; those reside in the `tests/` directory.
*   **Constraint Checking**: It is not responsible for evaluating the broader set of specification constraints (Φ); that is the role of the `SpecOracleAgent`.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `validation/` directory as a Python package and re-export key functions like `select_tests` and `run_tests`.
*   **Interfaces**: Provides the public API for the validation toolkit to the `FixerAgent` and other agents.

### 2.2. `selection.py`

*   **Responsibilities**:
    *   To implement the targeted test selection algorithm based on the dependency graph and coverage map.
    *   To provide a primary function `select_tests(changed_files: set[str]) -> list[str]` that returns the list of test files/nodes to execute.
*   **Data Models**: None.
*   **Algorithms**:
    1.  Load the dependency graph `G` and coverage map `K`.
    2.  Check for staleness of `G` and `K` and return a flag if they need rebuilding.
    3.  Given the input `changed_files`, compute the reverse-dependency closure `RDep(changed_files)` using a Breadth-First or Depth-First Search on `G`.
    4.  Combine the sets to get the total impacted code: `impacted_code = changed_files ∪ RDep(changed_files)`.
    5.  Iterate through the coverage map `K` to find all tests `t` that cover any file in `impacted_code`.
    6.  Add the mandatory "guard tests" (a configurable list of critical smoke tests).
    7.  Return the unique, sorted list of selected tests.
*   **Tests**: A `test_selection.py` will use mock graphs and coverage maps to assert that the algorithm correctly identifies the impacted tests for various change scenarios, including changes to leaf nodes, core libraries, and handling of import cycles.

### 2.3. `types.py`

*   **Responsibilities**:
    *   To implement delta typechecking to avoid re-checking the entire codebase on every change.
    *   To provide a function `run_delta_typecheck(changed_files: set[str]) -> TypeCheckResult`.
*   **Data Models**: `TypeCheckResult(exit_code: int, report: str, files_checked: list[str])`.
*   **Algorithms**:
    1.  Load the dependency graph `G`.
    2.  Compute the reverse-dependency closure `RDep(changed_files)`.
    3.  The set of files to check is `files_to_check = changed_files ∪ RDep(changed_files)`.
    4.  Invoke the configured typechecker (e.g., `mypy`) with the `files_to_check` list.
    5.  Capture and return the results.
*   **Tests**: A `test_types.py` will use a mock dependency graph and mock files to ensure that the correct subset of files is passed to the typechecker for different change scenarios.

### 2.4. `test_runner.py`

*   **Responsibilities**:
    *   To provide a secure and robust wrapper around the project's test command (e.g., `pytest`).
    *   To accept a list of specific tests to run.
    *   To capture the `exit_code`, `stdout`, and `stderr`.
    *   To parse structured test reports (e.g., JUnit XML) to extract pass/fail counts, timings, and failure details.
    *   To hash the full report for inclusion in proof bundles, ensuring verifiability.
*   **Data Models**: `TestRunResult(exit_code: int, passed: int, failed: int, skipped: int, duration_s: float, report_hash: str, report_content: str)`.
*   **Security**: This module executes external processes and is a potential security risk. It must:
    *   Use a strict allowlist for the base command (`pytest`, `npm`).
    *   Sanitize all arguments passed to the command to prevent shell injection.
    *   Execute within the sandboxed worktree with restricted permissions.
*   **Tests**: `test_test_runner.py` will use mock `subprocess.run` calls to simulate different test outcomes (pass, fail, error) and assert that the runner correctly parses the results and handles errors.

### 2.5. `coverage_index.py`

*   **Responsibilities**:
    *   To generate the test-to-file coverage map (K).
    *   To run the full test suite with coverage enabled (e.g., `pytest --cov`).
    *   To parse the coverage report (e.g., `.coverage` file or JSON output) into a canonical format: `dict[str, set[str]]` mapping test nodes to the source files they execute.
    *   To save this map to a file (e.g., `var/index/coverage.json`) with a hash of the code tree it corresponds to, to detect staleness.
*   **Data Models**: The coverage map dictionary.
*   **Algorithms**: Parsing of the coverage tool's output format.
*   **Tests**: `test_coverage_index.py` will use sample coverage reports in different formats to ensure the parsing logic is correct and robust.

### 2.6. `dep_graph.py`

*   **Responsibilities**:
    *   To generate the module dependency graph (G).
    *   To use static analysis (e.g., `LibCST` or `ast` module) to parse all source files in the project.
    *   To extract all `import` and `from ... import` statements to build a directed graph of dependencies.
    *   To save this graph to a file (e.g., `var/index/dep_graph.json`) with a hash of the code tree it corresponds to, to detect staleness.
*   **Data Models**: The dependency graph, likely represented as a `dict[str, set[str]]` where keys are modules and values are the set of modules they import.
*   **Algorithms**: Abstract Syntax Tree (AST) traversal to find import nodes. Graph traversal (BFS/DFS) for computing closures.
*   **Tests**: `test_dep_graph.py` will use a set of mock Python files with various simple, relative, and circular imports to verify that the generated graph is accurate.

---

## 3. Math & Guarantees (from README)

This directory's primary guarantee is **efficiency with soundness**.

*   **Efficiency**: By using targeted validation, the system avoids the O(N) cost of a full validation run for every small change, making the feedback loop much faster. This directly contributes to a lower "Effort" term in the `P` formula, allowing more valuable work to be done within the same budget.
*   **Soundness**: The guarantee of soundness is maintained by the **full audit gate**. While targeted validation is used for intermediate steps, the `QEDSupervisor` is configured to never accept a final solution without proof that at least one full test suite run has passed since the last code change. The selection algorithms are designed to be conservative (it's better to run an extra unnecessary test than to miss a necessary one), and the system's self-recovery mechanisms (`recovery/`) are responsible for rebuilding the indices if they become stale, further ensuring the integrity of the selection process.

---

## 4. Routing & Awareness

This directory is the **single source of truth for structural awareness** in the pForge system. The `dep_graph.py` module provides the foundational data that allows the entire system to understand how the code is interconnected. This awareness is consumed by:

*   `selection.py` and `types.py` for targeted validation.
*   `orchestrator/router.py` to determine the blast radius of changes.
*   `agents/predictor_agent.py` which might use graph metrics (like fan-in/fan-out) as features for its risk model `β`.

This centralized, explicit representation of the code's structure is a key differentiator from systems that rely on simple file-based heuristics.

---

## 5. Token & Budget Hygiene

This directory's operations are purely local and deterministic. They do not consume LLM tokens. By making the validation loop faster, this directory indirectly helps conserve the "time" component of the resource budget, allowing the `Planner` to allocate more of its budget to token-intensive tasks if needed.

---

## 6. Operational Flows

*   **Index Rebuild Flow (triggered by Self-Repair Agent)**:
    1.  `SelfRepairAgent` detects that `var/index/dep_graph.json` is stale (its associated code hash doesn't match the current tree).
    2.  It triggers a `RECOVERY.GRAPH_REBUILD` task.
    3.  A recovery process invokes `dep_graph.py`.
    4.  `dep_graph.py` scans the entire codebase, builds a new graph, and saves it with the new code hash.
    5.  A similar flow exists for the coverage map.
*   **Targeted Validation Flow (within FixerAgent)**:
    1.  `FixerAgent` applies a patch to files `ΔF`.
    2.  It calls `selection.select_tests(changed_files=ΔF)`.
    3.  The function returns a list of tests `T_0`.
    4.  `FixerAgent` calls `test_runner.run_tests(tests=T_0)`.
    5.  The runner executes `pytest` and returns a `TestRunResult`.
    6.  The `FixerAgent` includes the `selection` rationale and the `TestRunResult` in its proof bundle.

---

## 7. Testing & Backtests

*   **Unit Tests**: Each module will have focused unit tests as described in the blueprint section.
*   **Integration Tests**:
    *   `targeted_then_full_test.py`: This is a critical integration test. It will simulate a `Fixer` run where a targeted test set passes, but a subsequently introduced full audit test fails, ensuring the QED gate works. It will then repeat with a case where both pass.
*   **Backtesting**: The `verifier.py` will use the tools in this directory to ensure the honesty of historical proofs. When verifying a `FIX.PATCH_APPLIED` event, it will:
    1.  Call `selection.py` with the same `changed_files` from the proof.
    2.  Assert that the `selected_tests` list in the proof matches the output of the selection algorithm.
    3.  Call `test_runner.py` with the same tests on the same code snapshot.
    4.  Assert that the `exit_code` and report hash match the proof.
    This guarantees that the validation process was not tampered with or misrepresented in the historical record.

---

## 8. Security & Policy

The `test_runner.py` is the only component in this directory with significant security implications. It must be hardened against command injection by using `subprocess.run` with an explicit list of arguments rather than a raw string, and by validating that the test files it is asked to run are legitimate test files within the sandbox. The indexers (`dep_graph.py`, `coverage_index.py`) must also be hardened to handle malformed or malicious source files without crashing or entering into a vulnerable state.

---

## 9. Readme Cross-Reference

The `validation/` directory is the practical implementation of the "efficiency" aspect of the puzzle-solving framework described in the `README.md`.

| Validation Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `selection.py`, `types.py` | Represents the intelligent search strategy. Instead of re-checking the entire puzzle after every move, the solver intelligently focuses only on the connections involving the piece that was just moved and its neighbors. |
| `dep_graph.py` | Building the dependency graph is equivalent to understanding the "shape" of the puzzle pieces and how they are designed to interconnect *before* starting the assembly. |
| `test_runner.py` | The act of physically trying to fit a piece into a spot and seeing if it "clicks" (passes) or not (fails). |
| Full Audit Gate | The final check at the end, where the solver looks over the entire completed puzzle to make sure every single piece is perfectly aligned, even in areas that weren't recently touched. |

This directory provides the mechanisms that allow pForge to be both fast in its iterative loop and rigorously correct in its final conclusion.
