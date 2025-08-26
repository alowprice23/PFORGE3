# PLAN: `policies/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `policies/` directory provides a centralized, human-readable, and configurable location for all of the system's core security policies. By externalizing these critical definitions from the application code, this directory makes the security posture of pForge transparent, auditable, and easy to modify without requiring code changes. It serves as the single source of truth for "what is allowed" and "what is considered sensitive."

**Scope of Ownership**:

*   **Cryptographic Signing Policy (`signing/`)**: It owns the public keys used for verifying message signatures and the documented operational procedure for key rotation. It defines the root of trust for message authenticity.
*   **Data Redaction Policy (`redaction/`)**: It owns the definitive set of patterns used to identify and scrub sensitive information (secrets, PII) from all data before it is logged or included in proofs. It also owns the sample data used to test and document this policy.

**Explicitly Not in Scope**:

*   **Policy Enforcement Logic**: This directory contains only the *definition* of the policies, not the code that *enforces* them. The implementation of the signature verification logic resides in `proof/signatures.py`, and the implementation of the redaction engine resides in `proof/redaction.py`.
*   **General Application Configuration**: This directory is strictly for security policies. Other application settings (ports, feature flags, etc.) belong in the `config/` directory.

---

## 2. File-by-File Blueprints

### 2.1. `signing/` Subdirectory

This subdirectory manages the policy for ensuring the authenticity and integrity of AMP messages.

*   **`public.pem`**:
    *   **Purpose**: This file contains the public key (in PEM format) corresponding to the private key used to sign all AMP events. It is the public root of trust for the entire system.
    *   **Format**: A standard PEM file containing an Ed25519 public key.
    *   **Security**: This file is public and intended to be checked into version control. The corresponding private key **must never** be committed and should be managed as a high-priority secret (e.g., via environment variables or a secure vault).
*   **`rotate.md`**:
    *   **Purpose**: A critical operational document that provides a step-by-step checklist for an administrator to perform a zero-downtime rotation of the cryptographic signing keys.
    *   **Content**: The document will detail the following procedure:
        1.  Generating a new Ed25519 key pair.
        2.  A "dual-signing" period where the system signs events with both the old and new keys, allowing consumers to gradually adopt the new public key.
        3.  The process for updating the `public.pem` file and distributing it to all verifying components.
        4.  The final retirement of the old key.
        5.  Commands for verifying the new key is active.

### 2.2. `redaction/` Subdirectory

This subdirectory manages the policy for preventing data leakage.

*   **`patterns.yaml`**:
    *   **Purpose**: This file provides a configurable, machine-readable list of all patterns that the redaction engine should look for.
    *   **Format**: A YAML file containing a list of objects, where each object has a `name` (a human-readable identifier for the secret type) and a `pattern` (a PCRE-compatible regular expression).
    *   **Example**:
        ```yaml
        - name: "aws_access_key"
          pattern: "(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"
        - name: "private_key_pem_header"
          pattern: "-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"
        - name: "generic_api_key"
          pattern: "[a-zA-Z0-9_\\-]{32,128}" # Example, needs refinement
        ```
*   **`samples.md`**:
    *   **Purpose**: This document serves as both documentation and a source of test cases for the redaction policy. It provides clear examples of text that should and should not be redacted.
    *   **Content**: A markdown file with sections for each pattern in `patterns.yaml`. Each section will contain:
        *   A "Before" block with sample text containing the secret.
        *   An "After" block showing the expected output after redaction (e.g., `api_key: "[REDACTED]"`).
        *   Negative examples of text that looks similar but should not be redacted.

---

## 3. Math & Guarantees (from README)

This directory provides the foundation for the **guarantee of cryptographic integrity and policy enforcement**.

*   **Integrity (`signing/`)**: The public key in `public.pem` is the mathematical artifact that allows any component in the system to verify that a message has not been tampered with since it was signed. This is a direct application of public-key cryptography to ensure the integrity of the proofs and events that the system relies on.
*   **Policy as Code (`redaction/`)**: The `patterns.yaml` file turns the abstract policy of "don't leak secrets" into a concrete, machine-readable, and verifiable set of mathematical patterns (regular expressions). This guarantees that the redaction policy is applied consistently and transparently across the entire system.

---

## 4. Routing & Awareness

This directory has no routing logic. Its role in awareness is to provide a single, central point of reference that security-sensitive modules are "aware" of. The `proof/redaction.py` module is aware of `policies/redaction/patterns.yaml` and loads its rules from there. This makes the system's security policy easy to audit.

---

## 5. Token & Budget Hygiene

This directory has no impact on token budgets.

---

## 6. Operational Flows

*   **Signature Verification Flow**:
    1.  The `proof/verifier.py` module receives an AMP event with a signature.
    2.  It calls `proof/signatures.py`.
    3.  The `signatures.py` module loads the `policies/signing/public.pem` file from disk.
    4.  It uses the public key to verify the signature against the message content.
*   **Redaction Flow**:
    1.  The `proof/redaction.py` module is initialized.
    2.  It loads and compiles all the regular expressions from the `policies/redaction/patterns.yaml` file.
    3.  When its `scrub()` method is called with a data payload, it applies these compiled regexes to find and replace any sensitive data.

---

## 7. Testing & Backtests

The contents of this directory are critical inputs for the test suites of other modules.

*   **`test_redaction.py`**: This test will load `patterns.yaml` and use the text from `samples.md` to create a comprehensive suite of test cases. It will assert that all secrets in the "Before" blocks are correctly redacted and that the text in the "Negative examples" is left untouched.
*   **`test_signatures.py`**: The tests for the signature module will use a temporary, test-generated key pair that follows the same PEM format as `public.pem` to ensure the key loading and parsing logic is correct.

---

## 8. Security & Policy

This entire directory is dedicated to defining the security policies of the application. Its existence and structure are a security feature in themselves, promoting transparency and auditability. The key security considerations are:

*   **Key Management**: The `rotate.md` document is a critical security procedure. Its clarity and correctness are essential for maintaining the long-term security of the system's message bus.
*   **Pattern Quality**: The effectiveness of the redaction policy depends entirely on the quality and comprehensiveness of the regular expressions in `patterns.yaml`. This file should be subject to regular review by a security team.

---

## 9. Readme Cross-Reference

This directory provides the implementation of the fundamental "safety rules" for the puzzle-solving environment from the `README.md`.

| Policy Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `signing/` | The rule that ensures every move made by a solver is verifiably theirs and has not been altered by someone else. It's the equivalent of having a unique, tamper-proof signature on every action log entry. |
| `redaction/` | The rule that forbids writing down any sensitive information (like the password to the room where the puzzle is being solved) on the puzzle board itself, where it could be seen by others. |

This directory ensures that the pForge system operates with a transparent, auditable, and robust security posture.
