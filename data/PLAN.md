# PLAN: `data/` Directory

## 1. Directory Purpose & Scope

**Purpose**: To provide a standard, version-controlled location for all sample data, test cases, and benchmarks used to develop, test, and demonstrate the pForge system. This directory contains the "puzzles" that pForge is designed to solve, serving as the ground truth for evaluating its performance and correctness.

**Scope of Ownership**:

*   **Sample Repositories (`sample_repos/`)**: It owns any small, self-contained sample projects used for quick demonstrations, smoke tests, and onboarding examples.
*   **Benchmark Suite (`puzzlebench/`)**: It owns the formal `puzzlebench` suite, which includes a set of representative repositories with known defects, and the metadata that describes them. This is the primary dataset for performance and accuracy benchmarking.

**Explicitly Not in Scope**:

*   **Runtime Artifacts**: This directory does not contain any runtime-generated data, logs, or databases. That data belongs in the `var/` directory.
*   **Test Code**: It does not contain the `pytest` or `jest` code that *uses* this data to perform verification. That code resides in the `tests/` directory.
*   **Production Data**: The data here is for testing and demonstration purposes only and should not contain any production code or secrets.

---

## 2. File-by-File Blueprints

### 2.1. `sample_repos/` Subdirectory

This directory contains small, easy-to-use repositories for quick checks.

*   **`tiny_todo_app.zip`**:
    *   **Purpose**: A canonical small project for smoke tests, end-to-end tests, and live demonstrations. It is designed to be small enough to be analyzed and fixed by pForge in under a minute.
    *   **Content**: A simple web application with a React frontend and a Flask backend.
    *   **Known Defects**: It will be pre-seeded with a small number of well-defined bugs that pForge is expected to fix, such as:
        1.  A missing `DELETE` route in the Flask API.
        2.  A hardcoded secret key in the Flask app.
        3.  An unused import and a formatting issue in the React frontend.
        4.  A failing unit test in the backend.

### 2.2. `puzzlebench/` Subdirectory

This directory contains the formal, structured benchmark suite for rigorous performance evaluation.

*   **`metadata.json`**:
    *   **Purpose**: The central index for the `puzzlebench` suite. It provides the ground-truth data that allows the `verifiers/` scripts to score pForge's performance quantitatively.
    *   **Schema**: A JSON object containing a list of `entries`. Each entry will have:
        *   `id`: A unique identifier for the benchmark (e.g., "001").
        *   `name`: A human-readable name (e.g., "url_shortener").
        *   `language`: A list of primary languages (e.g., `["go", "react"]`).
        *   `loc`: The approximate lines of code.
        *   `ground_truth`: An object containing the known number of issues: `{"gaps": 12, "misfits": 3, "false_pieces": 1}`.
        *   `archive`: The path to the repository's `.tar.gz` file within the `repos/` directory.
*   **`repos/`**:
    *   **Purpose**: A directory to store the compressed archives of the benchmark repositories.
    *   **Content**: A collection of `.tar.gz` files, one for each entry in `metadata.json`. This keeps the main repository from being cluttered with dozens or hundreds of source files from other projects.

---

## 3. Math & Guarantees (from README)

This directory provides the **Ground Truth** for the mathematical framework, which guarantees that the system's performance can be objectively and repeatably measured.

*   **Denominator for Efficiency (`E`)**: The `ground_truth.gaps` value in `metadata.json` serves as the authoritative `TotalIssues` denominator when calculating the efficiency score `E` for a benchmark run. This prevents the system from "looking good" by simply failing to detect issues and ensures that the score reflects the actual proportion of known problems that were solved.
*   **Basis for KPI Calculation**: The data in this directory is the foundation for the KPIs calculated by the `verifiers/`. For example, the `verifiers/` can calculate the precision and recall of the `ObserverAgent` by comparing the issues it found against the ground-truth numbers in the metadata.

---

## 4. Routing & Awareness

This directory is not involved in routing. It provides "problem awareness" to the testing and verification systems.

---

## 5. Token & Budget Hygiene

This directory has no direct impact on token budgets.

---

## 6. Operational Flows

*   **End-to-End Test Execution Flow**:
    1.  The `e2e/qed_gate_end_to_end.py` test is initiated by the CI pipeline.
    2.  The test logic uses the `data/sample_repos/tiny_todo_app.zip` file as the input for a `pforge onboard` operation.
    3.  It then runs the `pforge doctor` command and waits for the known bugs in the sample app to be fixed.
*   **Benchmark Verification Flow**:
    1.  An operator or a CI job runs pForge on a benchmark from `data/puzzlebench/repos/`.
    2.  After the run is complete, the `verifiers/kpi_report.py` script is executed.
    3.  The script loads `data/puzzlebench/metadata.json` to retrieve the ground-truth data for that benchmark.
    4.  It compares the results of the pForge run (from the AMP log) against the ground truth to generate a performance report.

---

## 7. Testing & Backtests

The data in this directory is not tested itself; it is the **input data for the test suite**. The correctness of the tests in `tests/e2e/` and the scripts in `verifiers/` depends on the stability and consistency of the data in this directory. Any change to a benchmark repository or its metadata should be treated as a change that could require updates to the test suite.

---

## 8. Security & Policy

*   **Vetting of Test Data**: All sample repositories included in this directory must be carefully vetted to ensure they do not contain any real secrets, sensitive information, or malicious code. Since pForge is designed to analyze and potentially execute code, the input data must be trusted.
*   **Dependencies**: The dependencies listed in the sample projects (e.g., in `requirements.txt`) should also be vetted for security vulnerabilities.

---

## 9. Readme Cross-Reference

This directory provides the collection of "puzzles" for the puzzle-solving machine from the `README.md`.

| Data Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `sample_repos/tiny_todo_app.zip` | A simple, 16-piece "starter puzzle" used to make sure the solver knows the basic rules of the game. |
| `puzzlebench/` | A collection of puzzles of varying difficulty (e.g., 100-piece, 500-piece, 1000-piece puzzles) that are used to formally train and evaluate the solver's skill, speed, and accuracy. |
| `metadata.json` | The "picture on the box" for each benchmark puzzle. It tells you exactly what the finished puzzle should look like (the ground truth) so you can objectively score the solver's performance. |

This directory makes the testing and evaluation of pForge rigorous and data-driven.
