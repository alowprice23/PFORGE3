# PLAN: `docs/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `docs/` directory provides comprehensive, clear, and well-structured documentation for all aspects of the pForge system. This directory serves as the canonical source of truth for developers, operators, security auditors, and advanced users. Its purpose is to demystify the system's complex internals, making its architecture, operational procedures, APIs, and foundational principles accessible and understandable.

**Scope of Ownership**:

*   **Architectural Documentation (`architecture.md`)**: It owns the high-level overview of the system's design, components, and their interactions.
*   **Operational Guides (`runbook.md`)**: It owns the standard operating procedures (SOPs) for deploying, managing, and troubleshooting the system.
*   **API and Interface References (`api_reference.md`)**: It owns the detailed reference for all external interfaces, including the REST API and the CLI.
*   **Core Logic and Theory (`math_proofs.md`, `prompt_library.md`)**: It owns the definitive explanations of the mathematical framework and the prompt engineering strategies that form the intellectual core of pForge.
*   **Security and Verification Guides (`safety_policy.md`, `backtesting_guide.md`)**: It owns the documentation that details the system's security posture and the procedures for auditing its performance and correctness.

**Explicitly Not in Scope**:

*   **Implementation-Level Plans**: It does not contain the detailed, file-by-file `PLAN.md` files for each directory; those reside within their respective directories.
*   **Source Code or Configuration**: This directory contains only documentation in markdown format. All code, configuration, and policies are owned by their respective directories.
*   **Marketing or User-Facing Website Content**: The documentation here is technical and aimed at internal or advanced users, not the general public.

---

## 2. File-by-File Blueprints

### 2.1. `architecture.md`

*   **Purpose**: To provide a "map" of the pForge system for developers.
*   **Content**:
    *   **High-Level Diagrams**: Will include C4 model diagrams (System Context, Container, Component) to show the static structure.
    *   **Sequence Diagrams**: Will illustrate key operational flows, such as the "bug fix cycle" or the "preflight check," showing how the major components and agents interact over time.
    *   **Component Overview**: A section for each top-level directory, briefly explaining its purpose and its primary interactions with other components.
*   **Audience**: Developers (new and existing).

### 2.2. `runbook.md`

*   **Purpose**: To be the first place an on-call operator looks when an alert fires or a problem occurs.
*   **Content**:
    *   **Deployment Checklist**: A step-by-step guide for deploying or upgrading pForge in a new environment.
    *   **Alerting Playbooks**: A section for each major Prometheus alert (e.g., `EfficiencyStalled`, `BudgetExceeded`). Each playbook will contain:
        1.  The meaning of the alert.
        2.  First steps for diagnosis (e.g., "Check the Grafana dashboard," "Run `pforge status`").
        3.  Common causes and their resolutions.
    *   **Manual Procedures**: Checklists for operational tasks like key rotation, database migration, or manually triggering a recovery job.
*   **Audience**: System operators, SREs.

### 2.3. `api_reference.md`

*   **Purpose**: To be the definitive reference for all machine-to-machine and user-to-machine interfaces.
*   **Content**:
    *   **REST API**: A detailed, endpoint-by-endpoint description of the API provided by the `server/`. Each endpoint will have its path, method, required headers, request body schema, and possible response schemas (including error responses). This can be semi-automated using FastAPI's OpenAPI generation.
    *   **WebSocket/SSE API**: A description of the real-time event streams, including the topics, the schema for each event type, and example payloads.
    *   **CLI Reference**: A man page-style reference for the `pforge` command, detailing every subcommand, its arguments, and its options.
*   **Audience**: Developers integrating with pForge, advanced users, and test automation engineers.

### 2.4. `prompt_library.md`

*   **Purpose**: To act as a version-controlled catalog of all prompt templates used for interacting with LLMs.
*   **Content**:
    *   A section for each prompt (e.g., `fixer_patch_generation`, `intent_routing`).
    *   For each prompt, it will include:
        *   Its version number.
        *   Its purpose.
        *   A list of input variables.
        *   The full prompt template text.
        *   A description of the expected output format (e.g., "a unified diff in a JSON object").
    *   A changelog for prompts to track tuning and performance improvements.
*   **Audience**: Developers working on agent logic, prompt engineers.

### 2.5. `math_proofs.md`

*   **Purpose**: To be the academic "whitepaper" for the pForge system, detailing its theoretical foundation.
*   **Content**:
    *   Formal definitions of all core mathematical objects: Σ, Φ, E, H, P, β, Γ.
    *   Derivations and explanations of the key formulas, such as the `E_intelligent` formula and the CVaR-adjusted priority `P_cvar`.
    *   A description of the algorithms used, such as the knapsack solver for planning and the minimal hitting set for conflict resolution.
*   **Audience**: System architects, researchers, anyone who wants to understand *why* pForge works the way it does.

### 2.6. `safety_policy.md`

*   **Purpose**: To be the central document describing pForge's security architecture and policies.
*   **Content**:
    *   A description of the sandboxing mechanism and the path safety policy.
    *   An explanation of the capability token system and the principle of least privilege for agents.
    *   Details on the data redaction pipeline and its goals.
    *   Information on the egress control and command allowlist policies.
    *   The key rotation policy and its importance.
*   **Audience**: Security auditors, system operators, developers.

### 2.7. `backtesting_guide.md`

*   **Purpose**: To explain how to use pForge's own tools to verify the correctness and performance of a past run.
*   **Content**:
    *   An explanation of what a `ProofBundle` is and what data it contains.
    *   A step-by-step guide on how to use the `pforge verify` CLI command.
    *   A description of the key performance indicators (KPIs) that the verifier calculates (e.g., Precision@Action, Escape Rate) and how to interpret them.
*   **Audience**: Developers, QA engineers, system auditors.

---

## 3. Math & Guarantees (from README)

This directory provides the guarantee of **Transparency and Understandability**. The `math_proofs.md` file makes the entire theoretical foundation of the system explicit, reviewable, and unambiguous. This ensures that the system's logic is not a "black box" and can be independently understood and verified.

---

## 4. Routing & Awareness

This directory provides **Human Awareness**. It is the primary mechanism by which human developers, operators, and users become aware of the system's design, intended behavior, and operational state. Without this documentation, the system would be opaque and difficult to trust or maintain.

---

## 5. Token & Budget Hygiene

This directory has no direct impact on token budgets.

---

## 6. Operational Flows

The documents in this directory are central to key operational flows, particularly for humans.

*   **Onboarding a New Developer**: The flow starts with `architecture.md` for a system overview, followed by the relevant `PLAN.md` files for their area of focus.
*   **Responding to a Production Alert**: The flow starts with the `runbook.md`, which guides the operator through diagnosis and resolution.
*   **Performing a Security Audit**: The flow starts with `safety_policy.md` and `architecture.md`, followed by using the `backtesting_guide.md` to verify claims.

---

## 7. Testing & Backtests

The documentation itself should be "tested" via a continuous process of peer review. All documentation should be reviewed for clarity, accuracy, and completeness as part of the pull request process for any related code changes. The `api_reference.md` can be used to generate automated contract tests to ensure the implementation never drifts from its documented specification.

---

## 8. Security & Policy

The `safety_policy.md` is the canonical human-readable description of the system's security posture. The `runbook.md` contains the procedures for responding to security incidents. The `api_reference.md` clearly defines the security expectations for each endpoint (e.g., "Requires Authorization").

---

## 9. Readme Cross-Reference

This directory is a deep dive into every concept introduced in the main `README.md` and the puzzle-solving dialogue.

| Docs File | README.md Concept Cross-Reference |
| :--- | :--- |
| `math_proofs.md` | The unabridged, formal "textbook" version of the puzzle-solving formulas developed throughout the dialogue. |
| `architecture.md` | The detailed blueprint of the "puzzle-solving machine" itself, showing how all the conceptual parts are engineered to work together. |
| `runbook.md` | The "user manual" for the person operating the machine, telling them how to turn it on, what the dials do, and what to do if it makes a strange noise. |

This directory ensures that the knowledge behind pForge is not just embedded in its code but is also explicitly available for humans to read, understand, and build upon.
