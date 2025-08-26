# PLAN: `proof/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `proof/` directory is the cryptographic and logical foundation of trust in the pForge system. Its purpose is to provide the infrastructure for creating, signing, verifying, and managing **proof bundles**—the verifiable artifacts that underpin the "Proof or It Didn't Happen" design principle. This directory transforms abstract claims of success (e.g., "tests passed," "patch applied") into tamper-evident, auditable, and machine-checkable evidence.

**Scope of Ownership**:

*   **Proof Bundle Assembly (`bundle.py`)**: It owns the canonical data structure for a `ProofBundle` and the logic for assembling its constituent parts (test results, constraint checks, metric snapshots, etc.) into a single, coherent object.
*   **Cryptographic Signatures (`signatures.py`)**: It owns the implementation of digital signatures (e.g., HMAC-SHA256 for local mode, ed25519 for production) used to guarantee the authenticity and integrity of all AMP events and proof bundles.
*   **Proof Verification (`verifier.py`)**: It owns the engine that performs backtesting and verification. This verifier can take a historical proof bundle and independently re-compute and verify every claim within it, from re-hashing the code tree to re-running the specified tests.
*   **Capability Tokens (`capabilities.py`)**: It owns the system for issuing and verifying short-lived, scoped capability tokens, which serve as the primary authorization mechanism for agents performing privileged actions.
*   **Data Redaction (`redaction.py`)**: It owns the pipeline for scrubbing sensitive information (secrets, PII) from any data before it is included in a proof or published to a log, ensuring that proofs do not become a data leakage vector.
*   **Backtesting CLI (`backtest_cli.py`)**: It provides the human-facing command-line interface for invoking the verifier on past sessions.

**Explicitly Not in Scope**:

*   **Generating Proof Content**: The `proof/` directory does not generate the *data* that goes into a proof. For example, it does not run tests (that's `validation/`), evaluate constraints (that's `agents/spec_oracle_agent.py`), or calculate metrics (that's `orchestrator/efficiency_engine.py`). It only **assembles and secures** the evidence provided by other components.
*   **Policy Decision Making**: It does not decide *what* the security or correctness policies are. It only provides the mechanisms to *enforce* them. The policies themselves are defined in `config/policies.yaml` and evaluated by the `SpecOracleAgent`.
*   **Agent Logic**: It contains no agent-specific logic, although all agents are clients of this directory's services.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `proof/` directory as a Python package and to re-export key classes and functions for convenience (e.g., `ProofBundle`, `sign_amp`, `verify_capability`).
*   **Interfaces**: Provides the public API for the proof system to the rest of the pForge application.

### 2.2. `bundle.py`

*   **Responsibilities**:
    *   To define the canonical `ProofBundle` Pydantic model, which includes fields for `tree_sha`, `venv_lock_sha`, `constraints`, `tests`, `metrics`, `planner`, `effort`, and the final `qed` flag.
    *   To provide a builder function, `assemble_proof_bundle(...)`, that takes evidence from various sources and constructs a valid `ProofBundle` object.
    *   To perform structural validation on a bundle to ensure all required fields are present for a given claim type.
*   **Data Models**: `ProofBundle`, `ProofObligation` (imported from `orchestrator/signals.py` or defined locally).
*   **Algorithms**: The assembly function will be a straightforward data aggregation and validation process.
*   **Tests**: Unit tests to ensure a `ProofBundle` can be created, validated, serialized, and deserialized. Tests should cover cases with missing or malformed data.

### 2.3. `verifier.py`

*   **Responsibilities**:
    *   To provide the core function `verify_proof_bundle(bundle: ProofBundle, amp_event: AMP) -> VerificationResult`.
    *   To implement the step-by-step verification logic:
        1.  Verify the signature on the AMP event using `signatures.py`.
        2.  Check out the exact code tree specified by `bundle.tree_sha` from the CAS (`storage/cas.py`).
        3.  Re-create the exact environment specified by `bundle.venv_lock_sha`.
        4.  Re-run the exact tests specified in `bundle.tests.selection` and assert that the exit code matches.
        5.  Re-evaluate the constraints listed in `bundle.constraints` and assert that the outcomes match.
        6.  Re-compute the metrics and assert they are consistent with the proof.
*   **Data Models**: `VerificationResult(is_valid: bool, discrepancies: list[str])`.
*   **Algorithms**: This module is an orchestration of verification steps. The most complex part is managing the sandboxed environment for re-running tests.
*   **Security**: This is the ultimate auditor. Its correctness is paramount for the trust of the entire system.
*   **Tests**: This module requires extensive integration testing. A `test_verifier.py` will use a "golden" set of AMP events and associated artifacts (code snapshots, test reports) and assert that the verifier correctly validates the good proofs and invalidates a set of deliberately tampered proofs.

### 2.4. `signatures.py`

*   **Responsibilities**:
    *   To abstract away the underlying cryptographic library (`cryptography` package).
    *   To provide two simple functions: `sign(data: bytes, private_key: bytes) -> bytes` and `verify(data: bytes, signature: bytes, public_key: bytes) -> bool`.
    *   To handle key loading from PEM files or environment variables. For local-only mode, it will default to a stable HMAC-SHA256 implementation using a shared secret from `.env`.
*   **Data Models**: None.
*   **Algorithms**: Implements the Ed25519 signature algorithm (or HMAC-SHA256 as a fallback).
*   **Security**: This is a core cryptographic component. It must be implemented carefully to avoid common pitfalls like timing attacks (by using `hmac.compare_digest`).
*   **Tests**: Unit tests with known key pairs and messages to ensure that signing and verification work correctly, and that verification fails for tampered messages or incorrect keys.

### 2.5. `capabilities.py`

*   **Responsibilities**:
    *   To define the `Capability` token schema (a JWT or similar structure) containing fields for `scope`, `actor`, `op_id`, `exp` (expiration), and `nonce`.
    *   To provide an `issue_token(payload: dict, private_key: bytes) -> str` function for the `Orchestrator`.
    *   To provide a `verify_token(token: str, public_key: bytes) -> dict` function that checks the signature, expiration, and nonce.
    *   To manage a nonce store to prevent token replay attacks.
*   **Data Models**: `Capability` (Pydantic model).
*   **Algorithms**: JWT (JWS) generation and validation. Nonce checking against a persistent store (e.g., a SQLite table in `storage/sqlite/`).
*   **Security**: This is the heart of the system's authorization model. Correctly implemented, it enforces the principle of least privilege.
*   **Tests**: Unit tests for token issuance and verification, including tests for expired tokens, tokens with invalid signatures, and replayed nonces.

### 2.6. `redaction.py`

*   **Responsibilities**:
    *   To provide a single function `scrub(data: Any) -> (Any, RedactionReport)`.
    *   To maintain the set of redaction patterns (regexes for secrets, PII) loaded from `policies/redaction/patterns.yaml`.
    *   To recursively traverse nested data structures (dicts, lists) and apply the redaction patterns.
    *   To produce a report of what was redacted (counts per pattern), without including the sensitive data itself.
*   **Data Models**: `RedactionReport(redacted_counts: dict[str, int])`.
*   **Algorithms**: Recursive dictionary/list traversal and regex substitution.
*   **Security**: This is a critical data loss prevention (DLP) component. Its patterns must be kept up-to-date.
*   **Tests**: Unit tests with a variety of nested data structures containing known secrets to ensure they are all found and scrubbed correctly, and that the report is accurate.

### 2.7. `backtest_cli.py`

*   **Responsibilities**:
    *   To provide the `pforge verify` command-line interface.
    *   To parse command-line arguments (e.g., session ID, AMP log file path).
    *   To invoke the `verifier.py` engine on the specified session data.
    *   To print a human-readable summary of the verification results, including KPIs like Precision@Action and escape rate.
*   **Interfaces**: This is a client of `verifier.py` and is part of the main `cli/` application.
*   **Tests**: Tested via end-to-end tests of the CLI.

---

## 3. Math & Guarantees (from README)

The `proof/` directory provides the implementation of the **guarantees** that make the mathematical framework trustworthy.

*   **Verifiability**: The entire directory exists to make the system's operations verifiable. The `verifier.py` is the embodiment of this, providing a backtestable procedure to confirm that the mathematical claims made by the system (e.g., `ΔE > 0`) are supported by the ground-truth data.
*   **Integrity**: `signatures.py` provides a cryptographic guarantee that the data within a proof has not been altered since it was signed by the originating agent. This prevents tampering and ensures that the inputs to any verification are authentic.
*   **Reproducibility**: By anchoring every proof to a `tree_sha` and `venv_lock_sha`, the `bundle.py` module guarantees that the context of any claim is reproducible. The `verifier` can check out the exact same state to re-run the computation, eliminating "it worked on my machine" issues.

---

## 4. Routing & Awareness

This directory fosters **trust awareness**. By verifying signatures and capability tokens, the system can be aware of which messages and actors are legitimate. The `verifier.py` allows the system (or a human operator) to become aware of any discrepancies between claims and reality, providing a powerful feedback mechanism to correct the models of other agents.

---

## 5. Token & Budget Hygiene

This directory's operations are computationally inexpensive and do not use LLMs. It has no direct impact on token budgets, but it plays a crucial role in verifying the *value* of token spend by auditing the outcomes of LLM-driven actions.

---

## 6. Operational Flows

*   **Proof Assembly Flow**: An agent like `Fixer` has a result. It gathers the raw evidence (diff, test log). It calls `bundle.assemble_proof_bundle` to create the `ProofBundle`. It then calls `signatures.sign` on the bundle (or the parent AMP event) before publishing.
*   **Capability Check Flow**: An agent like `Fixer` receives a `FixTask` that requires writing to a file. The `Orchestrator` includes a capability token in the task payload. Before writing, the `Fixer` calls `capabilities.verify_token` on the token. If verification fails, it rejects the task and emits an error event.
*   **Backtesting Flow**: A user runs `pforge verify --session <id>`. The CLI invokes `verifier.py`. The verifier loads the AMP log for the session, and for each proof-carrying event, it checks out the corresponding code snapshot from the CAS, re-runs the validation, and compares the results, printing a final report.

---

## 7. Testing & Backtests

This directory is both a subject of tests and a provider of testing tools. Its own test suite must be exceptionally rigorous.

*   **Golden Data**: The tests for `verifier.py` will rely on a "golden" dataset: a small, hand-crafted set of code snapshots, AMP events, and proof bundles, some of which are valid and some of which are deliberately broken (e.g., bad signature, failing test that is claimed to pass). The tests will assert that the verifier correctly classifies every item in this set.
*   **Cryptographic Tests**: Tests for `signatures.py` and `capabilities.py` must cover all security-critical edge cases, such as handling of malformed keys, expired tokens, and replayed nonces.

---

## 8. Security & Policy

This directory is the primary implementation layer for the system's security and trust policies.

| Policy | Implemented By |
| :--- | :--- |
| Authenticity & Integrity | `signatures.py` |
| Authorization (Least Privilege) | `capabilities.py` |
| Data Loss Prevention (DLP) | `redaction.py` |
| Auditability & Non-repudiation | `verifier.py`, `bundle.py` |

It provides the tools to enforce the policies defined in `config/policies.yaml`.

---

## 9. Readme Cross-Reference

The `proof/` directory is the engineering realization of the trust and verifiability that the `README.md`'s puzzle-solving framework implicitly requires. A solution to a puzzle is only a solution if it can be independently checked.

*   **`S(Σ,t) = 1`**: The `qedsupervisor` may claim the puzzle is solved, but the `verifier` is what allows a third party to independently confirm that `S(Σ,t)` is indeed `1`.
*   **Backtracking `B(Σ)` and Risk `R(Σ)`**: The proof bundles provide the data needed to analyze why backtracking occurred and to build the risk models. Without a verifiable history of what was tried and what failed, the system could not learn.

This directory ensures that pForge is not just a "black box" that produces fixes, but a transparent, evidence-based reasoning system.
