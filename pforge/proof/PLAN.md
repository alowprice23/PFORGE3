# PLAN: `proof/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `proof/` directory is the cryptographic and logical foundation of pForge's "Proof or It Didn't Happen" principle. It provides the tools and infrastructure for creating, signing, and verifying the proof bundles that accompany every significant AMP event. This directory ensures that every claim made by an agent is not just a statement, but a verifiable, auditable, and tamper-proof artifact.

**Scope of Ownership**:

*   **Proof Bundle Construction (`bundle.py`)**: It owns the logic for assembling proof bundles, which includes attaching the content-addressed hashes of the code tree (`tree_sha`) and the environment (`venv_lock_sha`).
*   **Verification Logic (`verifier.py`)**: It owns the master verifier that can take a proof bundle and re-run all the checks to confirm its validity. This is used for backtesting and auditing.
*   **Cryptographic Signatures (`signatures.py`)**: It owns the implementation of the digital signature scheme (ed25519/HMAC) used to sign and verify AMP envelopes.
*   **Capability Tokens (`capabilities.py`)**: It owns the logic for creating and verifying the capability tokens that grant agents permission to perform specific actions.
*   **Data Redaction (`redaction.py`)**: It owns the implementation of the redaction engine that scrubs sensitive information from payloads and logs.
*   **Backtesting CLI (`backtest_cli.py`)**: It provides a command-line interface for running the verifier on a historical session and calculating key performance indicators (KPIs).

**Explicitly Not in Scope**:

*   **Agent Logic**: This directory does not contain any agent logic. It provides services that the agents use.
*   **State Management**: It does not manage the global `PuzzleState`. It consumes it to perform its verification checks.
*   **Policy Definitions**: The data for the policies (e.g., public keys, redaction patterns) is stored in the `policies/` directory. This directory contains the code that uses that data.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `proof/` directory as a Python package.

### 2.2. `bundle.py` [x]

*   **Responsibilities**: To provide a `ProofBundleBuilder` class that simplifies the creation of valid proof bundles.
    *   It takes the tree SHA and venv lock SHA as inputs.
    *   It provides methods to add constraint checks, test results, metrics, and other proof components.
    *   It ensures that the final bundle conforms to the `ProofBundle` Pydantic model.
*   **Interfaces**: Used by all agents that need to create proof bundles (e.g., `FixerAgent`, `SpecOracleAgent`).

### 2.3. `verifier.py` [x]

*   **Responsibilities**: To implement the master backtesting verifier.
    *   It takes a proof bundle and a historical session log as input.
    *   It re-computes all hashes and re-runs all checks to verify the proof's claims.
    *   It can be used to audit the system's behavior and to ensure that the "Proof or It Didn't Happen" guarantee is being met.
*   **Algorithms**: This module contains the logic for re-hydrating a historical state from the CAS and re-running tests and constraint checks.
*   **Interfaces**: Used by the `backtest_cli.py`.

### 2.4. `signatures.py` [x]

*   **Responsibilities**: To provide a simple, high-level API for signing and verifying AMP envelopes.
    *   It abstracts away the details of the underlying cryptographic library (e.g., `cryptography`).
    *   It supports both ed25519 for production and HMAC for simple local-only mode.
    *   It loads the public key from `policies/signing/public.pem`.
*   **Security**: This is a critical security component. Its implementation must be correct and robust.
*   **Interfaces**: Used by `messaging/amp.py` to sign and verify all AMP events.

### 2.5. `capabilities.py` [ ]

*   **Responsibilities**: To manage the capability tokens that authorize agents to perform actions.
    *   It provides functions to create, sign, and verify capability tokens.
    *   It enforces the scope, actor, and expiration of the tokens.
    *   It uses a nonce store (via `storage/sqlite/`) to prevent replay attacks.
*   **Security**: This is the core of the system's permission model, ensuring that agents can only do what they are explicitly authorized to do.
*   **Interfaces**: Used by the `Orchestrator` to issue tokens and by the `BaseAgent` and various middleware to verify them.

### 2.6. `redaction.py` [ ]

*   **Responsibilities**: To implement the data redaction engine.
    *   It loads the redaction patterns from `policies/redaction/patterns.yaml`.
    *   It provides a function to scrub sensitive information from text and data structures.
    *   It returns the redacted data along with a count of the redactions performed.
*   **Security**: Prevents the leakage of sensitive information into logs, metrics, or LLM prompts.
*   **Interfaces**: Used by all agents and services that handle potentially sensitive data.

### 2.7. `backtest_cli.py` [ ]

*   **Responsibilities**: To provide a `pforge verify` command for backtesting.
    *   It takes a session log as input.
    *   It uses the `verifier.py` to check all the proofs in the session.
    *   It computes and displays high-level KPIs like `Precision@Action` and the escape rate of the targeted test selection.
*   **Interfaces**: This is a command-line tool, intended to be used by developers and operators.

---

## 3. Math & Guarantees (from README)

The `proof/` directory is the implementation of the "proof" concept that is central to the pForge system. Every mathematical claim made by the system is ultimately backed by a proof bundle that is created and verified by the components in this directory. The digital signatures provide a cryptographic guarantee of authenticity, and the verifier provides a logical guarantee of correctness. This directory is what makes the system's claims **backtestable** and **auditable**.
