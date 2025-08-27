# PLAN: `validation/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `validation/` directory provides the tools and infrastructure for verifying the correctness of the code in the sandbox. It is responsible for running tests, performing type checks, and managing the data (coverage maps, dependency graphs) that enables targeted, efficient validation. This directory is what allows pForge to be "fast without cheating," providing rapid feedback on changes while maintaining a high degree of confidence in the correctness of the code.

**Scope of Ownership**:

*   **Targeted Test Selection (`selection.py`)**: It owns the logic for selecting the minimal sound subset of tests to run after a code change, based on the reverse-dependency graph and the test coverage map.
*   **Delta Type Checking (`types.py`)**: It owns the logic for running the type checker (mypy/pyright) on only the files affected by a change.
*   **Test Execution (`test_runner.py`)**: It owns the wrapper around the test runner (pytest), which is responsible for invoking the tests, capturing their results, and hashing the JUnit report.
*   **Coverage Indexing (`coverage_index.py`)**: It owns the logic for building and reading the test coverage map and for detecting when the map is stale.
*   **Dependency Graph Indexing (`dep_graph.py`)**: It owns the logic for building and reading the import dependency graph using `LibCST`.

**Explicitly Not in Scope**:

*   **Test Definitions**: This directory does not contain the tests themselves. Those reside in the `tests/` directory.
*   **Agent Logic**: It provides services to the agents (especially the `FixerAgent`), but does not contain any agent logic itself.
*   **Specification Constraints**: The evaluation of the high-level specification constraints (Φ) is owned by the `SpecOracleAgent`.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `validation/` directory as a Python package.

### 2.2. `selection.py` [ ]

*   **Responsibilities**: To implement the targeted test selection logic.
    *   It takes a set of changed files as input.
    *   It uses the dependency graph to compute the reverse-dependency closure.
    *   It uses the coverage map to select the tests that cover the changed files and their dependents.
    *   It includes a set of "guard" tests that are always run.
*   **Algorithms**: Uses graph traversal (BFS) to compute the reverse-dependency closure.
*   **Interfaces**: Used by the `FixerAgent` to select the tests to run after applying a patch.

### 2.3. `types.py` [ ]

*   **Responsibilities**: To implement delta type checking.
    *   It takes a set of changed files as input.
    *   It computes the reverse-dependency closure to determine the full set of files that need to be re-checked.
    *   It invokes the type checker on this subset of files.
*   **Interfaces**: Used by the `FixerAgent`.

### 2.4. `test_runner.py` [ ]

*   **Responsibilities**: To provide a robust wrapper around the test runner (pytest).
    *   It can run the entire test suite or a targeted subset of tests.
    *   It captures the exit code and the JUnit report.
    *   It hashes the JUnit report to provide a verifiable proof of the test results.
    *   It keeps track of which tests have been run since the last patch, to enforce the full audit requirement for QED.
*   **Interfaces**: Used by the `FixerAgent` and the `QEDSupervisor`.

### 2.5. `coverage_index.py` [ ]

*   **Responsibilities**: To manage the test coverage map.
    *   It can invoke the test runner with coverage enabled to generate a new coverage report.
    *   It parses the coverage report (JSON format) and stores it in a format that is easy to query.
    *   It includes logic to detect when the coverage map is stale (e.g., older than a certain age, or does not cover recently changed files).
*   **Interfaces**: The coverage map is used by `selection.py`. The staleness detection is used by the `SelfRepairAgent`.

### 2.6. `dep_graph.py` [ ]

*   **Responsibilities**: To manage the import dependency graph.
    *   It uses `LibCST` to parse all the Python files in the repository and build a graph of the import relationships between them.
    *   It provides a function to compute the reverse-dependency closure for a given set of files.
*   **Algorithms**: Uses static analysis (parsing Python code) and graph traversal.
*   **Interfaces**: The dependency graph is used by `selection.py` and `types.py`.

---

## 3. Math & Guarantees (from README)

The `validation/` directory is what makes the system's claims about correctness verifiable and efficient.

*   **Targeted Validation**: The targeted test selection and delta type checking are direct implementations of the "fast without cheating" principle. They allow the system to get rapid feedback on changes without sacrificing the guarantee of a full audit before final acceptance.
*   **Proof of Correctness**: The `test_runner.py` provides the raw data (exit codes, JUnit hashes) that is used to construct the proof bundles that are central to the system's operation.

The guarantee of this directory is that all validation will be performed in a way that is both efficient and sound, providing a high degree of confidence in the correctness of the code at every stage of the process.
