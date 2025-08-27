# PLAN: `docs/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `docs/` directory provides the comprehensive documentation for the pForge system. It is the single source of truth for the system's architecture, operational procedures, APIs, and mathematical foundations. This directory is what makes the pForge system understandable, maintainable, and extensible.

**Scope of Ownership**:

*   **Architectural Diagrams (`architecture.md`)**: It owns the high-level diagrams and descriptions of the system's architecture.
*   **Operational Runbooks (`runbook.md`)**: It owns the runbooks for on-call engineers, including procedures for handling common failures and alerts.
*   **API Reference (`api_reference.md`)**: It owns the reference documentation for the REST API, the WebSocket, and the AMP protocol.
*   **Prompt Library (`prompt_library.md`)**: It owns the versioned library of all the prompt templates used by the system's LLM clients.
*   **Mathematical Proofs (`math_proofs.md`)**: It owns the detailed explanation of the mathematical foundations of the system, including the definitions of all the core mathematical objects (Σ, Φ, E, H, etc.).
*   **Safety Policies (`safety_policy.md`)**: It owns the documentation for the system's security policies, including capabilities, redaction, and egress controls.
*   **Backtesting Guide (`backtesting_guide.md`)**: It owns the guide for how to use the backtesting tools to verify the system's claims.

**Explicitly Not in Scope**:

*   **Source Code**: This directory contains only documentation. All source code resides in the `pforge/` directory.
*   **Marketing Material**: This directory is for technical documentation, not marketing material.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `architecture.md` [ ]

*   **Responsibilities**: To provide a high-level overview of the system's architecture, including diagrams of the agent swarm, the event bus, and the content-addressed store.

### 2.2. `runbook.md` [ ]

*   **Responsibilities**: To provide a set of standard operating procedures for on-call engineers, including how to respond to common alerts and how to perform common maintenance tasks.

### 2.3. `api_reference.md` [ ]

*   **Responsibilities**: To provide a complete reference for the system's APIs, including the REST endpoints, the WebSocket events, and the AMP message schemas.

### 2.4. `prompt_library.md` [ ]

*   **Responsibilities**: To provide a versioned catalog of all the prompt templates used by the system, including the safety banners that are prepended to each prompt.

### 2.5. `math_proofs.md` [ ]

*   **Responsibilities**: To provide a detailed, formal explanation of the mathematical foundations of the system. This is the human-readable version of the `math_models/` directory.

### 2.6. `safety_policy.md` [ ]

*   **Responsibilities**: To document the system's security policies, including the capability model, the data redaction policies, and the network egress controls.

### 2.7. `backtesting_guide.md` [ ]

*   **Responsibilities**: To provide a guide for how to use the backtesting tools in the `proof/` directory to verify the system's claims.

---

## 3. Math & Guarantees (from README)

The `docs/` directory is where the mathematical guarantees of the system are made explicit and human-readable. The `math_proofs.md` file is the canonical reference for the mathematical foundations of the system, and the `backtesting_guide.md` explains how to verify that the implementation of the system is consistent with those foundations. This directory is what makes the system's claims about its mathematical rigor **transparent** and **understandable**.
