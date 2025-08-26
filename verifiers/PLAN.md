# PLAN: `verifiers/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `verifiers/` directory provides a suite of offline, post-hoc analysis and verification scripts. These tools are used to audit the historical performance, correctness, and efficiency of a completed pForge run by analyzing its output artifacts (AMP logs, CAS snapshots, databases). This directory is the ultimate arbiter of the "Proof or It Didn't Happen" principle, transforming the system's implicit claims into explicit, quantitative, and verifiable Key Performance Indicators (KPIs).

**Scope of Ownership**:

*   **KPI Calculation Scripts**: It owns the scripts for calculating all major system KPIs, such as `Precision@Action`, `Escape Rate`, and conflict resolution efficiency.
*   **Audit Logic**: It owns the logic for auditing the correctness of the system's most critical decisions, such as the firing of the QED (completion) gate.
*   **Reporting**: It owns the top-level script (`kpi_report.py`) that orchestrates all other verifiers and aggregates their results into a single, human-readable report.

**Explicitly Not in Scope**:

*   **Real-time Components**: These are **not** real-time agents or components. They are offline tools designed to be run by an operator or a CI job after a pForge session is complete.
*   **Application Logic**: This directory does not contain any of the core application logic for solving problems; it only analyzes the results of that logic.
*   **The Test Suite**: While it performs verification, it is distinct from the `tests/` directory. The `tests/` directory verifies the code's correctness before a commit, while the `verifiers/` directory analyzes the system's performance *after* a run.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `verifiers/` directory as a Python package.

### 2.2. `precision_at_action.py`

*   **Purpose**: To calculate the `Precision@Action` KPI, which measures how effective the `PlannerAgent` is at choosing actions that actually fix problems.
*   **Algorithm**:
    1.  Parse a session's AMP log.
    2.  Identify all `FIX.PATCH_APPLIED` events. This is the denominator (`Total Patches`).
    3.  For each such event, find the subsequent `SPEC.CHECKED` event for the same snapshot.
    4.  Compare the set of failing *blocking* constraints before and after the patch.
    5.  If at least one failing blocking constraint was fixed and no new blocking constraints were introduced, count it as a "True Positive".
    6.  Calculate `Precision = True Positives / Total Patches`.
*   **Output**: A JSON object containing the precision score, the number of true positives, and the total number of patches.

### 2.3. `escape_rate.py`

*   **Purpose**: To measure the "escape rate" of the targeted testing policy, i.e., how often a bug was missed by the targeted test set but would have been caught by the full suite.
*   **Algorithm**:
    1.  Parse an AMP log.
    2.  Find all `FIX.PATCH_APPLIED` events whose proof indicates that a *targeted* test set was run and passed.
    3.  Find the next `SPEC.CHECKED` event that indicates a *full audit* test run was performed on the same snapshot.
    4.  If the full audit run failed, this is an "escape".
    5.  Calculate `Escape Rate = Total Escapes / Total Targeted Runs`.
*   **Output**: A JSON object with the escape rate, total escapes, and total targeted runs.

### 2.4. `conflict_minimality.py`

*   **Purpose**: To verify that the `ConflictDetectorAgent` is correctly identifying the smallest possible set of edits to resolve a conflict.
*   **Algorithm**:
    1.  Parse an AMP log and find a `CONFLICT.FOUND` event.
    2.  From the proof, extract the conflict hypergraph (the mapping of violations to the sets of edits that caused them) and the `hitting_set` that the agent chose.
    3.  For each element `e` in the `hitting_set`, temporarily remove it and check if the remaining set still "hits" (intersects with) all the original conflict sets.
    4.  If such an element `e` exists, the original set was not minimal.
*   **Output**: A report of any `CONFLICT.FOUND` events where the hitting set was not minimal.

### 2.5. `qed_gate_audit.py`

*   **Purpose**: To audit the `QEDSupervisor`, ensuring it only fires the final `QED.EMITTED` event when all preconditions are met.
*   **Algorithm**:
    1.  Find the `QED.EMITTED` event in an AMP log.
    2.  Examine the window of events immediately preceding it.
    3.  Independently verify all QED gates:
        *   Was the last `SPEC.CHECKED` event fully successful for all blocking constraints?
        *   Was the last `EFF.UPDATED` event showing a stable, above-threshold `E` value?
        *   Were there any `CONFLICT.FOUND` events that were not followed by a `CONFLICT.RESOLVED`?
        *   Was there a successful full audit test run since the last patch?
*   **Output**: A boolean result of the audit, with a list of any violated gates.

### 2.6. `kpi_report.py`

*   **Purpose**: To act as the main entry point for the verification suite.
*   **Algorithm**:
    1.  Takes a session ID or log file path as input.
    2.  Calls the main function of each of the other verifier scripts in the directory.
    3.  Collects the JSON outputs from each script.
    4.  Aggregates them into a single, comprehensive report (either as a large JSON object or a formatted markdown file) and prints it to standard output.
*   **Interfaces**: The primary user interface for the verification suite.

---

## 3. Math & Guarantees (from README)

This directory provides the guarantee of **Post-Hoc Accountability**. It provides the tools to empirically measure and verify the system's performance against its mathematical goals.

*   **`precision_at_action.py`**: Directly measures how well the `Planner`'s `P` formula correlates with actual success (`ΔE > 0`).
*   **`escape_rate.py`**: Quantifies the real-world risk of the targeted validation shortcuts, allowing for data-driven tuning of the selection algorithm's conservatism.
*   **`conflict_minimality.py`**: Verifies the implementation of the minimal hitting set algorithm, a core concept from set theory used for logical reasoning.

This closes the loop, allowing the abstract mathematical models to be refined based on their measured, real-world performance.

---

## 4. Routing & Awareness

This directory is not involved in real-time routing. It provides **Historical Awareness** to human operators, allowing them to deeply understand the behavior, performance, and correctness of any past pForge run.

---

## 5. Token & Budget Hygiene

These scripts are local and do not consume LLM tokens.

---

## 6. Operational Flows

*   **A Developer wants to analyze a recent production run**:
    1.  The developer runs `python -m verifiers.kpi_report --session-id <id>`.
    2.  The `kpi_report.py` script fetches the corresponding AMP log from storage.
    3.  It invokes the other verifier scripts on the log file.
    4.  It prints a markdown report to the console, summarizing the key KPIs for that run, highlighting any anomalies or regressions.

---

## 7. Testing & Backtests

This entire directory is a backtesting tool, but it must be tested itself.
*   **Golden Log Files**: The test suite for this directory will include several small, hand-crafted "golden" AMP log files representing different scenarios (a successful run, a run with a test escape, a run with a non-minimal conflict set).
*   **Unit Tests**: Each verifier script will have a unit test that runs it against one of these golden logs and asserts that the calculated KPI matches the known correct value for that log.

---

## 8. Security & Policy

These are read-only analysis tools and have a low security risk profile. However, they parse potentially large and complex log files, so they must be robust against malformed or malicious input to prevent denial-of-service vulnerabilities in the analysis pipeline itself.

---

## 9. Readme Cross-Reference

This directory provides the tools for the "scientific method" to be applied to the puzzle-solving framework from the `README.md`. It's not enough for the solver to claim it has solved the puzzle; this directory allows an independent party to review the "game tape" and analyze its performance with mathematical rigor.

| Verifier Script | README.md Concept Cross-Reference |
| :--- | :--- |
| `precision_at_action.py` | Measures how "smart" the solver's moves were. Did it work on the right pieces at the right time? |
| `escape_rate.py` | Measures how often the solver's quick checks (targeted tests) caused it to miss a bigger problem that was only found later. |
| `qed_gate_audit.py` | Verifies the solver's claim that the puzzle is "finished," ensuring it didn't declare victory prematurely. |

This directory provides the final layer of trust in the system: the ability to independently and quantitatively verify its claims.
