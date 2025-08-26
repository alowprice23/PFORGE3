# PLAN: `messaging/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `messaging/` directory provides the definitive schema and transport abstraction for all inter-agent communication. It defines the universal language (AMP - Agent Message Protocol) and the reliable "postal service" (a Redis Streams wrapper) that the entire pForge agent swarm uses to collaborate. Its existence ensures that communication is structured, consistent, verifiable, and decoupled from the underlying transport technology.

**Scope of Ownership**:

*   **AMP Schema (`amp.py`)**: It owns the canonical Pydantic model for the `AMPMessage`. This includes all fields required for a robust, auditable event-driven system: idempotency keys (`op_id`), causality tracking (`causality`), actor identification, a strongly-typed action, a flexible payload, and a container for a proof bundle.
*   **Serialization/Deserialization**: It is responsible for the logic that converts `AMPMessage` objects to and from a wire format (JSON).
*   **Transport Abstraction (`redis_stream.py`)**: It owns the high-level, asynchronous wrapper for the message bus. This module provides simple `add` and `read` functions that hide the specific commands of the underlying technology (Redis Streams) and handle the graceful fallback to an in-memory substitute (`fakeredis`) for local-only mode.

**Explicitly Not in Scope**:

*   **Message Bus Implementation**: This directory does not implement the message bus itself. It is a client of a Redis server or the `fakeredis` library.
*   **Message Content Logic**: It does not contain any logic related to the *meaning* of the messages. It only defines their structure. The logic for producing and consuming messages resides entirely within the `agents/`.
*   **Cryptographic Signing**: While the AMP schema has a field for a signature, the actual signing and verification logic is owned by the `proof/signatures.py` module.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `messaging/` directory as a Python package and re-export the `AMPMessage` class and the primary stream interaction functions for easy access by other modules.
*   **Interfaces**: Provides `AMPMessage`, `stream_add`, and `stream_read` to the rest of the application.

### 2.2. `amp.py`

*   **Responsibilities**:
    *   To define the `AMPMessage` Pydantic model, which serves as the strict schema for all events.
    *   To ensure all required fields for an auditable, idempotent system are present: `op_id`, `at` (timestamp), `type`, `actor`, `causality`, `snap_sha`, `payload`, `proof`, and `sig`.
    *   To provide helper methods for serialization (`to_json`) and deserialization (`from_json`).
    *   To provide a validation function that can check the structural integrity of a message, ensuring it conforms to the protocol before it's sent or after it's received.
*   **Data Models**: `AMPMessage(BaseModel)`.
*   **Algorithms**: None. This module is purely for data modeling and validation.
*   **Tests**: A `test_amp.py` will perform round-trip testing (object -> JSON -> object) and validate that the model correctly rejects malformed dictionaries.

### 2.3. `redis_stream.py`

*   **Responsibilities**:
    *   To provide a simple, asynchronous API for interacting with the message bus.
    *   To implement `stream_add(redis: Redis, stream: str, msg: AMPMessage)` which serializes the message and uses the `XADD` command. It will also handle stream trimming (`maxlen`).
    *   To implement `stream_read(redis: Redis, streams: dict[str, str], ...)` which uses the `XREADGROUP` command to read from multiple streams for a consumer group, and deserializes the results back into `AMPMessage` objects.
    *   To implement the graceful fallback to `fakeredis`. The module will check for a `REDIS_URL` environment variable. If absent, it will instantiate and use a `fakeredis.FakeRedis` object, allowing the entire system to function in a local-only, dependency-free mode.
*   **Data Models**: None.
*   **Algorithms**: Logic to detect Redis availability and switch to the `fakeredis` client.
*   **Tests**: An integration test `test_redis_stream.py` will use `fakeredis` to test the `stream_add` and `stream_read` functions, ensuring that messages can be written and read correctly, and that cursors (`last_id`) are updated properly.

---

## 3. Math & Guarantees (from README)

This directory provides the foundational guarantees that allow the mathematical framework to be implemented in a distributed, multi-agent system.

*   **Causality and Auditability**: The `causality` field in the `AMPMessage` schema, combined with the immutable, append-only nature of Redis Streams, creates a verifiable causal log of all system operations. This allows any run to be perfectly reconstructed and audited, which is a prerequisite for backtesting the mathematical claims of the other modules.
*   **Idempotency**: The `op_id` field is a core guarantee. It ensures that if a message is delivered more than once (a common occurrence in distributed systems), the consuming agent can safely ignore the duplicate, preventing redundant computations or actions. This makes the system robust and resilient.

---

## 4. Routing & Awareness

This directory is the **substrate of all awareness** in pForge. No agent is aware of any other agent directly. Instead, awareness is mediated entirely through the message bus.

*   **Decoupled Communication**: Agents publish messages of a certain `type` without knowing who, if anyone, is listening. Other agents subscribe to the `type`s they are interested in. This creates a highly decoupled and extensible architecture.
*   **System-Wide Visibility**: By using a centralized bus, the state of the entire system can be observed by any component with the right permissions (like the UI's WebSocket forwarder or a debugging tool) simply by subscribing to the relevant streams. The `AMPMessage` schema ensures this visibility is structured and consistent.

---

## 5. Token & Budget Hygiene

This directory is not involved in token consumption.

---

## 6. Operational Flows

*   **Agent A Publishes an Event**:
    1.  Agent A's logic decides to publish a result.
    2.  It instantiates an `AMPMessage` object from `amp.py`, filling in the `type`, `payload`, and any `proof` data.
    3.  It calls `messaging.redis_stream.stream_add()` with the message.
    4.  The `redis_stream` module serializes the message and performs the `XADD` command to the Redis bus.
*   **Agent B Consumes an Event**:
    1.  Agent B's main loop calls `messaging.redis_stream.stream_read()`, specifying the stream(s) it subscribes to and its last seen message ID.
    2.  The `redis_stream` module calls `XREADGROUP`, receives a raw response from Redis.
    3.  It deserializes the raw data for each message into a validated `AMPMessage` object.
    4.  It returns the list of `AMPMessage` objects to Agent B for processing.

---

## 7. Testing & Backtests

*   **Unit Tests**: `test_amp.py` will ensure the `AMPMessage` schema is robust.
*   **Integration Tests**: `test_redis_stream.py` will use `fakeredis` to test the full add/read/ack cycle, ensuring the transport abstraction is reliable.
*   **Backtesting**: The `verifier` system is a primary consumer of this directory's work. During a backtest, it uses the `AMPMessage.from_json()` method to parse the historical event log that was generated by this messaging layer. The integrity and consistency of the `AMPMessage` schema are therefore critical for auditability.

---

## 8. Security & Policy

*   **Schema Enforcement**: By using a strict Pydantic model for `AMPMessage`, the system rejects any malformed messages, providing a basic layer of defense against malformed inputs from a potentially compromised agent.
*   **Signature Container**: The `sig` field in the `AMPMessage` schema provides the standardized location for the cryptographic signature. This allows consumers to easily find and verify the signature for any message, enforcing the system's authenticity and integrity policies.

---

## 9. Readme Cross-Reference

The `messaging/` directory is the practical implementation of the communication protocol for the "team of specialists" described in the `README.md`.

| Messaging Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `amp.py` | Defines the "shared mathematical vocabulary" and "common language" that the Formalizer, Solver, and Verifier agents use to communicate without needing to know about each other's internal state. |
| `redis_stream.py` | The underlying "communication channel" that allows the agents to collaborate and the "Coordinator" agent to orchestrate the workflow by passing the mathematical model and solution attempts between them. |

This directory ensures that the collaboration between agents is not ad-hoc but follows a formal, structured, and reliable protocol, which is a prerequisite for the system's complex, multi-step reasoning process.
