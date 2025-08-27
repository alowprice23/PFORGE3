# PLAN: `policies/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `policies/` directory holds the data and documentation for pForge's security policies, specifically those related to cryptographic signing and data redaction. Unlike the `config/` directory, which contains tunable parameters, this directory contains the raw data and procedural documents that enforce security guarantees. It is a critical component of the "Proof or It Didn't Happen" principle.

**Scope of Ownership**:

*   **Signing Keys**: It owns the public keys used for verifying the signatures on AMP events. The private keys are managed as secrets and are not stored here.
*   **Key Rotation Procedures**: It owns the documentation that describes the process for rotating the cryptographic keys.
*   **Redaction Patterns**: It owns the YAML file containing the regular expressions and denylists used to identify and redact sensitive information from logs and payloads.
*   **Redaction Samples**: It owns a set of examples and tests for the redaction patterns, which can be used to verify the effectiveness of the redaction engine.

**Explicitly Not in Scope**:

*   **Policy Enforcement Logic**: This directory contains the data and documentation for the policies, but the code that enforces these policies resides elsewhere (e.g., `proof/signatures.py`, `proof/redaction.py`).
*   **Private Keys**: Private keys are never stored in the repository.
*   **Operational Policies**: High-level operational policies (e.g., gating policies for QED) are defined in `config/policies.yaml`.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `signing/public.pem` [x]

*   **Responsibilities**: To provide the public key for verifying the signatures on AMP events. This key corresponds to the private key used by the agents to sign their messages.
*   **Security**: This file is public and can be distributed with the pForge system. It allows any consumer of the AMP bus to verify the authenticity and integrity of the messages.
*   **Interfaces**: Used by `proof/signatures.py` to verify AMP event signatures.

### 2.2. `signing/rotate.md` [x]

*   **Responsibilities**: To document the procedure for rotating the cryptographic keys. This includes:
    *   Generating a new key pair.
    *   Distributing the new public key.
    *   A transition period where both the old and new keys are valid.
    *   The final decommissioning of the old key.
*   **Security**: A clear and well-documented key rotation procedure is essential for maintaining the long-term security of the system.
*   **Interfaces**: This is a human-readable document and is not directly consumed by the application.

### 2.3. `redaction/patterns.yaml` [x]

*   **Responsibilities**: To define the patterns used to identify sensitive information. This file contains:
    *   A list of regular expressions for common secret formats (e.g., API keys, passwords).
    *   A denylist of file paths and directory names that should not be included in logs or payloads (e.g., `.ssh/`, `.aws/`).
*   **Security**: This file is the core of the data redaction engine, preventing sensitive information from leaking into logs or being sent to external LLMs.
*   **Interfaces**: Used by `proof/redaction.py` to scrub payloads and logs.

### 2.4. `redaction/samples.md` [x]

*   **Responsibilities**: To provide a set of examples and tests for the redaction patterns. This includes:
    *   Examples of text that should be redacted.
    *   Examples of text that should not be redacted (to avoid false positives).
*   **Testing**: This file can be used to generate unit tests for the redaction engine, ensuring that the patterns in `patterns.yaml` are effective and accurate.
*   **Interfaces**: This is a human-readable document, but can be parsed by a test runner to generate test cases for `proof/redaction.py`.

---

## 3. Math & Guarantees (from README)

The `policies/` directory provides the foundation for the "Proof or It Didn't Happen" guarantee. The cryptographic signatures on AMP events, verified using the public key in this directory, provide a mathematical guarantee of the authenticity and integrity of the messages. The redaction patterns are a key part of the safety constraints (Φ_safety) that must be satisfied for the system to be considered in a valid state.

---

## 4. Security & Policy

This directory is purely focused on security policy data. It is a critical component of the system's overall security posture, and its contents should be carefully managed and audited.
