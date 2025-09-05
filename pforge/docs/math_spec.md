# pForge Mathematical Specification

This document provides a detailed explanation of the mathematical models that form the foundation of the pForge system. These models are not merely heuristics; they are a formal framework for reasoning about code, measuring progress, and making decisions in a predictable and verifiable way.

## 1. The Formal Model

At its core, pForge treats a software project as a mathematical puzzle. The state of this puzzle is defined by a set of formal objects:

### 1.1. Global State Snapshot (Σ)

The entire state of the system at any given moment is captured in a global snapshot, denoted as Σ.

**Σ = (C, T, M, Θ)**

Where:

*   **C**: The **Codebase**, representing the source code itself (files, Abstract Syntax Trees (ASTs), diffs).
*   **T**: The **Test Corpus**, including the set of all tests and their outcomes (pass/fail).
*   **M**: The **Metrics**, a collection of quantitative measurements about the system's state (defined below).
*   **Θ**: The **Configuration**, which includes system settings, feature flags, and resource budgets.

### 1.2. Specification Constraints (Φ)

The specification, Φ, is a set of logical obligations that a "correct" or "solved" codebase must satisfy.

**Φ = {φ₁, φ₂, ..., φₖ}**

Each constraint `φᵢ` is a function that maps a given state Σ to a boolean value (`True` or `False`). A candidate state Σ' is considered acceptable if and only if `φᵢ(Σ') = True` for all `i`.

Examples of constraints include:

*   `All unit tests must pass.`
*   `There shall be no circular dependencies between modules.`
*   `No secrets shall be hard-coded in source files.`
*   `The code must adhere to the specified style guidelines.`

### 1.3. Candidate Solution (σ)

A candidate solution, σ, is a set of transformations (edits) that map one state Σ to a new state Σ'.

**σ: {τ₁, τ₂, ..., τₗ} where τ maps Σ ↦ Σ'**

The primary goal of the pForge system is to discover a solution σ that results in a state Σ' where all constraints in Φ are satisfied and the system's core efficiency metric is maximized.

## 2. Core Metrics: Progress & Priority

pForge uses a set of core metrics to quantify its progress and to prioritize its actions.

### 2.1. Efficiency (E): The Measure of Progress

The Efficiency score, E, is the primary objective function that the system seeks to maximize. It provides a high-level signal of the project's overall health and progress. The `pforge/math_models/efficiency.py` module contains a simplified version of this formula, while the `README.md` provides the more comprehensive version.

A simplified conceptual formula is:

**E = w₁ * (ClosedIssues / TotalIssues) - w₂ * H**

Where:

*   **w₁**, **w₂**: Tunable weights to balance the importance of closing issues versus reducing entropy.
*   **H**: The system's Entropy, a measure of disorder (see below).
*   **ε**: A small constant to prevent division by zero.

The change in E (ΔE) per action serves as the primary reward signal for the system's learning and adaptation processes.

### 2.2. Entropy (H): The Measure of Disorder

Entropy, H, is a measure of the irregularities and disorder within the codebase. A lower entropy score is better. The `pforge/math_models/entropy.py` module provides a simplified implementation based on the Shannon entropy of test results.

Conceptually, H aggregates various forms of disorder:

*   **Stylistic Entropy**: Deviations from the project's established coding style.
*   **Structural Entropy**: Complexity and irregularities in the codebase's structure, such as high cyclomatic complexity or "spaghetti" dependencies.
*   **Process Entropy**: Flakiness in tests or a high rate of noise in logs.

### 2.3. Action Priority (P): The Guide for Decision-Making

The Action Priority, P, is a formula used by the `PlannerAgent` to decide which task to work on next. The `pforge/math_models/priority.py` provides a simplified implementation.

The full conceptual formula is:

**Pⱼ = (Impactⱼ * Frequencyⱼ) / (Effortⱼ * Riskⱼ + ε)**

Where for a given action `j`:

*   **Impact**: The expected positive change in the Efficiency score (ΔE) or the criticality of the task (e.g., fixing a security vulnerability).
*   **Frequency**: How often the underlying defect pattern appears in the codebase.
*   **Effort**: The estimated cost (e.g., time, computational resources, number of lines to change) to apply and validate the fix.
*   **Risk (β)**: The probability that the proposed change will fail or introduce a new bug (see below).

### 2.4. Risk Prior (β): The Measure of Uncertainty

The Risk Prior, β, is a learned probability distribution that estimates the likelihood of a change in a particular module `m` causing a new issue.

**βₘ = P(new issue in module m | signals)**

The `PredictorAgent` is responsible for learning and maintaining this risk surface using signals from code metrics, change history, and test flakiness. The risk prior is a crucial input to the Action Priority formula, ensuring that pForge does not recklessly apply high-risk changes without sufficient potential reward.

## 3. Search, Validity, and Proof

pForge employs a systematic search process to find a valid solution, where every step is backed by a verifiable proof.

### 3.1. Transformation Validity

A proposed transformation `τ` is considered valid if and only if:

1.  All tests pass on the resulting codebase `τ(C)`.
2.  All specification constraints are satisfied: `∀ φᵢ ∈ Φ, φᵢ(τ(Σ)) = True`.

The `FixerAgent` is responsible for producing a **proof artifact** (e.g., a test hash and a constraint certificate) to demonstrate the validity of its transformations.

### 3.2. Heuristic Search with Backtracking

pForge searches for a solution over the space of possible edits using a heuristic search algorithm, such as A*. The cost function for the search is guided by the risk prior `β`. If a path of edits leads to an invalid state (a "conflict"), the system uses a minimal hitting set algorithm to identify the smallest set of edits to retract, allowing it to backtrack efficiently and continue searching along a more promising path.

### 3.3. Termination (QED)

The system declares that the puzzle is "solved" (Quod Erat Demonstrandum) when a state is reached where:

1.  All blocking specification constraints in Φ are satisfied.
2.  The efficiency score E meets or exceeds a configured threshold.
3.  There are no unresolved conflicts (Γ = ∅).

When these conditions are met, the system emits a signed `QED.EMITTED` event with the final proof bundle, certifying the solution.
