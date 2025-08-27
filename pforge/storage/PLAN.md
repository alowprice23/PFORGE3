# PLAN: `storage/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `storage/` directory provides all the persistence mechanisms for pForge. It is responsible for storing the content-addressed snapshots of the codebase, the SQLite databases for the constellation memory and other ephemeral data, and for managing file system locks. This directory is critical for the system's guarantees of reproducibility, auditability, and idempotency.

**Scope of Ownership**:

*   **Content-Addressable Storage (`cas.py`)**: It owns the implementation of the CAS, which is used to store immutable snapshots of the codebase. This includes the logic for creating and retrieving blobs, trees, and commits.
*   **SQLite Schemas (`sqlite/`)**: It owns the SQL schema definitions for all the SQLite databases used by the system, including the constellation memory, the capability nonce store, and the token budget ledger.
*   **File System Locks (`fslock.py`)**: It owns the implementation of the file system locks used to prevent race conditions when multiple agents or processes are writing to the sandbox.

**Explicitly Not in Scope**:

*   **Business Logic**: This directory contains only the low-level storage primitives. The business logic that uses these primitives resides in other directories (e.g., `sandbox/`, `memory/`).
*   **In-Memory State**: This directory is only concerned with persistent storage. In-memory state is managed by the `orchestrator/`.
*   **Messaging**: The messaging transport is owned by the `messaging/` directory.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `storage/` directory as a Python package.

### 2.2. `cas.py` [ ]

*   **Responsibilities**: To implement the content-addressed storage system.
    *   `write_blob`: Takes a byte string, computes its SHA-256 hash, and stores it in the object store.
    *   `read_blob`: Retrieves a blob from the object store by its hash.
    *   `write_tree`: Takes a list of file entries (path, mode, hash) and creates a tree object.
    *   `read_tree`: Retrieves a tree object by its hash.
    *   `write_commit`: Creates a commit object that points to a tree and a parent commit.
    *   `read_commit`: Retrieves a commit object by its hash.
*   **Algorithms**: Uses SHA-256 for content addressing. The storage layout is similar to Git's object store.
*   **Interfaces**: Used by `sandbox/fs_manager.py` to create and restore snapshots.

### 2.3. `sqlite/` Subdirectory

This directory contains the SQL schemas for the SQLite databases.

*   **`constellation_schema.sql` [ ]**: Defines the tables for the constellation memory, including `transitions` and `action_stats`.
*   **`nonces_schema.sql` [ ]**: Defines the table for storing the nonces used in capability tokens to prevent replay attacks.
*   **`budget_ledger_schema.sql` [ ]**: Defines the table for tracking the token spend for each LLM vendor.

### 2.4. `fslock.py` [ ]

*   **Responsibilities**: To provide a simple, robust file system lock.
    *   It should provide a context manager that acquires a lock on a file or directory and releases it on exit.
    *   It should be safe for use by multiple processes.
*   **Interfaces**: Used by any component that needs to perform atomic writes to the file system.

---

## 3. Math & Guarantees (from README)

The `storage/` directory is the foundation of the system's auditability and reproducibility.

*   **Content-Addressable Storage**: The CAS guarantees that every snapshot of the codebase has a unique, deterministic hash (`tree_sha`). This is what allows proof bundles to be tied to a specific, immutable state of the code.
*   **Constellation Memory**: The SQLite database for the constellation memory is the physical realization of the learning component of the system. It stores the raw data that the agentic CLI uses to improve its performance over time.
*   **Idempotency**: The nonce store in the SQLite database is a key part of the idempotency guarantee for capability tokens.

The guarantee of this directory is that all data will be stored in a consistent, durable, and verifiable manner, providing the foundation for the "Proof or It Didn't Happen" principle.
