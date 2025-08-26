# PLAN: `storage/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `storage/` directory provides the durable, verifiable, and transactionally-safe persistence layers for all of pForge's critical state. It is the system's long-term memory, responsible for ensuring that data, once written, is preserved with integrity and can be retrieved efficiently. This includes the content of the code itself, the agentic CLI's learned experiences, and essential operational ledgers.

**Scope of Ownership**:

*   **Content-Addressable Store (`cas.py`)**: It owns the low-level implementation of the CAS, which stores all file content as immutable, hashed blobs. This is the foundation for the verifiable snapshots used in proofs.
*   **Database Schemas (`sqlite/`)**: It owns the canonical SQL `CREATE TABLE` schemas for all SQLite databases used by the system. This includes the `constellation` memory for the CLI, the `nonces` table for security, and the `budget_ledger` for financial auditing.
*   **Low-Level File Utilities (`fslock.py`)**: It owns platform-agnostic, low-level utilities required for safe concurrent file access, such as file locks.

**Explicitly Not in Scope**:

*   **Data Interpretation**: The `storage/` directory is agnostic to the meaning of the data it stores. It saves and retrieves bytestrings and structured records but does not interpret them. The logic for building a code tree from CAS blobs resides in `sandbox/fs_manager.py`, and the logic for interpreting constellation data resides in `cli/` and `agentic/`.
*   **High-Level Abstractions**: It provides the primitive storage operations, not the high-level abstractions. For example, `sandbox/fs_manager.py` is a client of `cas.py` that understands the concept of "trees" and "commits".
*   **The Database Engine Itself**: It defines the schemas but does not implement the SQLite engine.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `storage/` directory as a Python package and re-export key functions or classes for use by other modules.
*   **Interfaces**: Provides a clean import surface for modules like `cas` and `fslock`.

### 2.2. `cas.py` (Content-Addressable Store)

*   **Responsibilities**:
    *   To provide low-level functions for writing to and reading from the CAS.
    *   `write_blob(data: bytes) -> str`: Takes a byte string, computes its SHA256 hash, writes the data to the object store if it doesn't already exist, and returns the hash.
    *   `read_blob(sha256_hash: str) -> bytes`: Takes a hash and returns the corresponding byte string from the object store.
    *   To manage the sharded directory structure of the object store (e.g., `var/snapshots/objects/ab/cdef...`) for efficient filesystem performance.
*   **Data Models**: None. It operates on raw bytes.
*   **Algorithms**: SHA256 hashing. Directory sharding based on the first few characters of the hash.
*   **Edge Cases**:
    *   **Hash Collisions**: Extremely unlikely with SHA256, but the logic should handle it gracefully (e.g., by verifying content on read if a collision were ever detected, though this is largely theoretical).
    *   **Corrupt Blobs**: `read_blob` should verify that the hash of the data it reads from disk matches the requested hash, raising a `DataCorruptionError` if it doesn't.
*   **Tests**: A `test_cas.py` will test the `write_blob` and `read_blob` functions, ensuring data integrity (read(write(data)) == data) and that hashes are correct. It will also test the corruption detection mechanism.

### 2.3. `sqlite/` Subdirectory

This directory contains the `.sql` files that define the schemas for the system's SQLite databases. This approach keeps the schema separate from the application code, making it easy to manage and version.

*   **`constellation_schema.sql`**:
    *   **Purpose**: Defines the tables for the agentic CLI's long-term memory.
    *   **Schema**:
        *   `transitions` table: Stores each step of an agentic run (`id`, `ts`, `context`, `action`, `command`, `rc`, `stdout`, `before_metrics`, `after_metrics`, `reward`).
        *   `action_stats` table: Stores the learned statistics for the UCB1/Thompson sampling policy (`context`, `action`, `n_pulls`, `mean_reward`).
*   **`nonces_schema.sql`**:
    *   **Purpose**: Defines the table for storing used nonces to prevent replay attacks on capability tokens.
    *   **Schema**: `capability_nonces` table (`nonce: str PRIMARY KEY`, `op_id: str`, `expires_at: int`).
*   **`budget_ledger_schema.sql`**:
    *   **Purpose**: Defines the table for creating a persistent, auditable log of all LLM token expenditures.
    *   **Schema**: `token_spend` table (`id`, `ts`, `vendor`, `op_id`, `prompt_tokens`, `completion_tokens`, `cost_usd`).

### 2.4. `fslock.py`

*   **Responsibilities**:
    *   To provide a simple, cross-platform context manager for acquiring and releasing a file lock.
    *   To use `fcntl.flock` on Unix-like systems and a compatible mechanism (e.g., via the `msvcrt` module or by creating/deleting a `.lock` file as a fallback) on Windows.
*   **Usage**:
    ```python
    from storage.fslock import file_lock

    with file_lock("path/to/shared/file.json"):
        # Safely read and write to the file
        ...
    ```
*   **Algorithms**: Implements a standard file locking pattern with timeouts to prevent deadlocks.
*   **Tests**: A `test_fslock.py` will use multiple processes or threads to attempt concurrent writes to a file and assert that the lock correctly serializes access, preventing data corruption.

---

## 3. Math & Guarantees (from README)

This directory is the foundation for the system's **guarantees of integrity and reproducibility**.

*   **Content-Addressing and Hashes**: The `cas.py` module is the implementation of the core mathematical concept that allows pForge to be verifiable. By storing all code as content-addressed blobs, the `tree_sha` in a proof becomes an immutable, mathematical fingerprint of the state. This guarantees that any two proofs referencing the same `tree_sha` are talking about the exact same code, down to the last byte. This is the bedrock of reproducibility.
*   **Transactional Integrity**: The use of SQLite, a database with ACID properties, guarantees that the critical operational data (constellation memory, budgets, nonces) is stored transactionally. This prevents data corruption from partial writes or concurrent access, ensuring the integrity of the system's memory and security state.

---

## 4. Routing & Awareness

The `storage/` directory provides **historical awareness**.

*   **CAS as History**: The CAS is a complete, immutable history of every state the codebase has ever been in. This allows the `verifier` to travel back in time to any `tree_sha` and re-run validation, providing perfect historical awareness.
*   **Constellation as Learned Memory**: The `constellation.sqlite` database provides the agentic CLI with awareness of its own past performance. By querying this database, the CLI can determine which actions have been most effective in a given context, allowing it to make increasingly intelligent decisions over time.

---

## 5. Token & Budget Hygiene

The `sqlite/budget_ledger_schema.sql` is the foundation for long-term budget auditing. While the `llm_clients/budget_meter.py` handles the real-time checking, this persistent ledger ensures that a complete, auditable history of all token spend is maintained, even across restarts. This allows for historical analysis of cost per feature, cost per agent, or cost per vendor.

---

## 6. Operational Flows

*   **CAS Write Flow**:
    1.  A client (like `sandbox/fs_manager.py`) has a block of data (e.g., a file's content).
    2.  It calls `cas.write_blob(data)`.
    3.  `cas.py` computes the SHA256 hash of the data.
    4.  It uses the hash to determine the storage path (e.g., `objects/ab/cdef...`).
    5.  If the file at that path does not exist, it writes the data.
    6.  It returns the hash to the client.
*   **Constellation Memory Update Flow**:
    1.  The `agentic/loop.py` completes an action and computes the reward.
    2.  It calls a function in `memory/constellation.py`.
    3.  `constellation.py` opens a connection to the `constellation.sqlite` database.
    4.  It executes `INSERT` and `UPDATE` statements (conforming to the schema in `storage/sqlite/`) to record the new transition and update the action statistics.
    5.  It commits the transaction.

---

## 7. Testing & Backtests

*   **Unit Tests**: Each module will have focused unit tests as described above. The SQLite schemas will be tested by creating an in-memory database and applying the `.sql` files, then performing basic CRUD operations to ensure they are valid.
*   **Backtesting**: The CAS is the absolute core of the backtesting process. The `verifier`'s first step is always to use `cas.py` to read the blobs and trees associated with a proof's `tree_sha`. The integrity of the CAS is what makes the entire "proof-or-it-didn't-happen" philosophy possible.

---

## 8. Security & Policy

*   **Data Integrity**: The use of SHA256 in the CAS guarantees that data cannot be altered without detection. If a blob file on disk is corrupted or maliciously changed, its hash will no longer match its filename, and `cas.read_blob` will raise an error.
*   **Replay Attack Prevention**: The `nonces_schema.sql` defines the storage for the nonce-based replay prevention mechanism used by the capability token system.
*   **Race Condition Prevention**: `fslock.py` provides a critical primitive for preventing data corruption in shared resources like index files, which could otherwise be a vulnerability.

---

## 9. Readme Cross-Reference

The `storage/` directory is the implementation of the "memory" that the puzzle solver in the `README.md` requires to learn and to be auditable.

| Storage Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `cas.py` | The perfect, immutable memory of every single configuration of the puzzle the solver has ever created. It allows the solver to go back to any previous state (`Σ`) to re-evaluate a decision. |
| `sqlite/constellation_schema.sql` | The solver's "long-term memory" or "experience". It remembers which sequences of moves (`Σ`) were efficient (`E`) and which led to dead ends (`B(Σ)`), allowing it to improve its strategy over time. |

This directory provides the solid, reliable foundation upon which the system's intelligence and verifiability are built.
