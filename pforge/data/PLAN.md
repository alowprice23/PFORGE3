# PLAN: `data/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `data/` directory contains all the sample data, benchmarks, and test corpora used by the pForge system. It is essential for testing, validating, and demonstrating the capabilities of the system. This directory provides the "puzzles" that the pForge system is designed to solve.

**Scope of Ownership**:

*   **Sample Repositories (`sample_repos/`)**: It owns the small, self-contained sample repositories that are used for demos and simple end-to-end tests.
*   **Benchmark Suite (`puzzlebench/`)**: It owns the `puzzlebench` suite, which is a collection of larger, more complex repositories with known issues. This suite is used for performance benchmarking and for measuring the system's effectiveness on a variety of real-world codebases.

**Explicitly Not in Scope**:

*   **Test Code**: The code for the tests that use this data resides in the `tests/` directory.
*   **Application Code**: This directory contains no application code.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `sample_repos/tiny_todo_app.zip` [x]

*   **Responsibilities**: To provide a small, intentionally broken sample project for demos and simple tests. It contains a simple Flask backend and a React frontend with known bugs.
*   **Interfaces**: Used by the `e2e/smoke_local_no_docker.py` test and by the `scripts/seed_demo.sh` script.

### 2.2. `puzzlebench/metadata.json` [ ]

*   **Responsibilities**: To provide a machine-readable index of all the benchmark repositories in the `puzzlebench` suite. Each entry contains:
    *   `id`: A unique identifier for the benchmark.
    *   `name`: A human-readable name for the benchmark.
    *   `language`: A list of the programming languages used in the benchmark.
    *   `loc`: The number of lines of code in the benchmark.
    *   `gaps`, `misfits`, `false_pieces`: The known number of issues in the benchmark, which are used to measure the system's performance.
    *   `archive`: The path to the tarball containing the benchmark repository.
*   **Interfaces**: Parsed by the benchmark test runner to execute the benchmarks.

### 2.3. `puzzlebench/repos/` Subdirectory

*   **Responsibilities**: To store the tarball archives of the benchmark repositories. Each tarball contains a complete Git repository with a known set of issues.
*   **Interfaces**: The tarballs are extracted by the benchmark test runner.

---

## 3. Math & Guarantees (from README)

The `data/` directory provides the ground truth for measuring the performance of the pForge system. The `puzzlebench` suite, with its known number of gaps, misfits, and false pieces, allows for the quantitative measurement of the system's ability to improve the efficiency score `E` of a codebase. This directory is what makes the system's claims about its puzzle-solving capabilities **falsifiable** and **measurable**.
