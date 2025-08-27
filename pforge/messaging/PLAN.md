# PLAN: `messaging/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `messaging/` directory provides the communication backbone of the pForge system. It defines the protocol (AMP) and the transport mechanism (Redis Streams) that all agents use to communicate. This directory is essential for the decoupled, event-driven architecture of pForge, allowing agents to collaborate without direct dependencies on each other.

**Scope of Ownership**:

*   **AMP Schema (`amp.py`)**: It owns the canonical definition of the Agent Message Protocol (AMP), including the Pydantic model for the message envelope and the logic for serializing and deserializing messages.
*   **Redis Stream Transport (`redis_stream.py`)**: It owns the thin, high-level wrapper around the Redis Streams API, providing simple functions for adding and reading messages from the bus. It also includes a hook for mirroring events to the WebSocket for the UI.

**Explicitly Not in Scope**:

*   **Message Content**: This directory defines the envelope for the messages, but it does not define the content of the payloads. That is the responsibility of the individual agents.
*   **Message Routing Logic**: While it provides the transport, it does not implement any logic for routing messages to specific agents. That is handled by the agents themselves through the pub/sub model.
*   **State Management**: It is a stateless transport layer and does not manage any part of the global `PuzzleState`.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `messaging/` directory as a Python package.

### 2.2. `amp.py` [x]

*   **Responsibilities**: To define the Agent Message Protocol (AMP).
    *   It provides a `AMPMessage` Pydantic model that defines the structure of all messages on the bus.
    *   It includes helper functions for creating, serializing, and deserializing AMP messages.
    *   It enforces the inclusion of essential metadata like the `op_id` for idempotency and the `snap_sha` for tying the message to a specific state of the codebase.
*   **Interfaces**: Used by all agents and services that send or receive messages on the AMP bus.

### 2.3. `redis_stream.py` [x]

*   **Responsibilities**: To provide a simple, robust interface to Redis Streams.
    *   It provides a `stream_add` function for publishing messages to a stream.
    *   It provides a `stream_read` function for consuming messages from one or more streams, managing the stream offsets automatically.
    *   It includes a `stream_iter` async generator for continuously yielding messages from a stream.
    *   It includes a hook to mirror events to the WebSocket consumer for the UI.
    *   It handles the connection to the Redis server and gracefully falls back to `fakeredis` in local-only mode.
*   **Interfaces**: Used by the `BaseAgent`'s AMP helper methods and by the WebSocket consumer.

---

## 3. Math & Guarantees (from README)

The `messaging/` directory is the transport layer for the mathematical proofs and claims that the agents generate. The guarantees of this directory are:

*   **Atomicity**: Each message is a single, atomic unit of communication.
*   **Ordered Delivery**: Redis Streams guarantees that messages are delivered in the order they were sent.
*   **Durability**: Messages are persisted in Redis, allowing for recovery and backtesting.
*   **Integrity**: The AMP schema, combined with the digital signatures from the `proof/` directory, ensures the integrity and authenticity of all messages.

This directory is what makes the "proof-carrying pipeline" a reality, providing a reliable and auditable channel for all inter-agent communication.
