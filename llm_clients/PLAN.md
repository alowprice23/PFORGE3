# PLAN: `llm_clients/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `llm_clients/` directory provides a standardized, robust, and policy-aware interface for all interactions with external Large Language Models (LLMs). It acts as a crucial abstraction layer, isolating the core agent logic from the implementation details of specific LLM providers. Its purpose is to make LLM calls safe, reliable, and economically managed.

**Scope of Ownership**:

*   **Provider-Specific Clients (`gemini_client.py`, `claude_client.py`, `openai_o3_client.py`)**: It owns the concrete client classes that handle the unique API schemas, authentication, and request/response formats for each supported LLM vendor.
*   **Resilience and Retry Logic (`retry.py`)**: It owns the generic, decorator-based mechanism for handling transient failures (e.g., network errors, rate limiting) with a mathematically sound exponential backoff strategy.
*   **Budget Enforcement (`budget_meter.py`)**: It owns the client-side logic for tracking and enforcing token budgets. It ensures that no LLM call is made if it would exceed the allocated quotas.
*   **Safety Guardrails (`guardrails.py`)**: It owns the pre-flight safety checks that are applied to all outgoing prompts. This includes scanning for secrets, preventing prompt injection, and ensuring that LLM usage complies with the system's operational policies.

**Explicitly Not in Scope**:

*   **Prompt Engineering**: This directory does not contain the logic for constructing the prompts themselves. The prompts are created by the `agents/` that are using the LLMs for a specific task. This directory only provides the transport mechanism.
*   **High-Level Task Routing**: It does not decide *which* LLM to use for a given task. That strategic decision is made by the `PlannerAgent` or a factory that consumes the clients.
*   **The LLM Services Themselves**: It is a client of external, third-party APIs and does not implement any language models.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `llm_clients/` directory as a Python package and to re-export the public client classes and the `retry` decorator.
*   **Interfaces**: Provides the main entry points for the LLM client library.

### 2.2. `gemini_client.py` [ ]

*   **Responsibilities**: To provide a simple, high-level client for Google's Gemini models.
    *   `__init__`: Initializes the official Google Generative AI client using an API key from the environment.
    *   `generate(prompt: str, ...)`: Takes a prompt string, formats it into the Gemini API's request schema, wraps the API call with the `@retry` decorator, performs budget checks via `budget_meter.py`, and parses the response to return a simple string.
*   **Dependencies**: `retry.py`, `budget_meter.py`, `guardrails.py`.

### 2.3. `claude_client.py` [ ]

*   **Responsibilities**: To provide a client for Anthropic's Claude models. Its structure will be nearly identical to the Gemini client, but adapted for the Anthropic API schema and authentication.
*   **Dependencies**: `retry.py`, `budget_meter.py`, `guardrails.py`.

### 2.4. `openai_o3_client.py` [~]

*   **Responsibilities**: To provide a client for OpenAI's models. Its structure will be nearly identical to the other clients, but adapted for the OpenAI API schema and authentication.
*   **Dependencies**: `retry.py`, `budget_meter.py`, `guardrails.py`.

### 2.5. `retry.py` [x]

*   **Responsibilities**: To provide a single, highly-reusable decorator `@retry_llm(...)`.
*   **Algorithms**: It will use the `tenacity` library to implement exponential backoff with jitter. This is a standard algorithm for preventing thundering herd problems and gracefully handling transient network or service failures. The decorator will be configurable for the number of retries and the types of exceptions to catch.
*   **Tests**: A `test_retry.py` will use a mock function that raises transient errors to assert that the decorator correctly retries the specified number of times with increasing delays.

### 2.6. `budget_meter.py` [x]

*   **Responsibilities**:
    *   To provide a `BudgetMeter` class that can be instantiated per-operation or per-agent.
    *   To implement the `check_and_spend(vendor: str, tokens: int) -> bool` method.
    *   This method will connect to the central `budget_ledger.sqlite` database and perform a transactional check to see if the requested spend is within the remaining quota for the given vendor and for the global budget. If it is, it records the spend and returns `True`. Otherwise, it returns `False`.
*   **Data Models**: Interacts with the schema defined in `storage/sqlite/budget_ledger_schema.sql`.
*   **Tests**: A `test_budget_meter.py` will use an in-memory SQLite database to test the spend/check logic, including cases of sufficient funds, insufficient funds, and concurrent requests.

### 2.7. `guardrails.py` [ ]

*   **Responsibilities**:
    *   To provide a `check_prompt_safety(prompt: str) -> SafetyReport` function.
    *   This function will run a series of checks on the prompt text before it is sent to an LLM.
    *   **Secret Scanning**: Use the patterns from `policies/redaction/patterns.yaml` to check for secrets.
    *   **Egress Guard**: If in local-only mode, check for and flag any URLs or IP addresses.
    *   **Command Injection**: Check for patterns that look like attempts to construct malicious shell commands.
*   **Data Models**: `SafetyReport(is_safe: bool, reasons: list[str])`.
*   **Tests**: A `test_guardrails.py` will test the `check_prompt_safety` function with a variety of safe and unsafe prompts and assert that it correctly identifies the violations.

---

## 3. Math & Guarantees (from README)

This directory provides the guarantee of **controlled and safe resource consumption**.

*   **Budget Constraints**: The `budget_meter.py` is the direct enforcement mechanism for the `B_tokens` constraint in the `Planner`'s optimization problem. This guarantees that the system's use of expensive LLM resources stays within the planned limits.
*   **Exponential Backoff**: The `retry.py` module's use of exponential backoff is a mathematically sound strategy for dealing with contention and transient failures in a distributed system, guaranteeing that pForge behaves like a good citizen when interacting with external APIs.

---

## 4. Routing & Awareness

This directory provides **provider awareness** and **cost awareness**.

*   By abstracting each vendor into a separate client, it allows a higher-level component (like the `PlannerAgent`) to be aware of the different capabilities and costs of each LLM (as defined in `config/llm_providers.yaml`) and to route tasks to the most appropriate model. For example, a simple bug-finding task might be routed to the cheapest, fastest model, while a complex code generation task is routed to the most powerful one.

---

## 5. Token & Budget Hygiene

This entire directory is the cornerstone of token and budget hygiene. It provides the mechanisms for:

1.  **Pre-flight Checking**: Ensuring a call is within budget before it's made.
2.  **Real-time Accounting**: Recording the actual token usage for every call in a persistent ledger.
3.  **Auditing**: Providing the data needed for long-term analysis of cost efficiency.

---

## 6. Operational Flows

*   **A Standard LLM Call from an Agent**:
    1.  An agent (e.g., `FixerAgent`) constructs a prompt.
    2.  It instantiates the appropriate client, e.g., `client = ClaudeClient(...)`.
    3.  It calls `client.generate(prompt)`.
    4.  Inside the client, `guardrails.check_prompt_safety(prompt)` is called. If unsafe, it raises an exception.
    5.  The client estimates the token cost and calls `budget_meter.check_and_spend(...)`. If it returns `False`, it raises a `BudgetExceededError`.
    6.  The client makes the API call, wrapped in the `@retry_llm` decorator.
    7.  If the call fails with a transient error, `retry.py` handles the backoff and retry.
    8.  On success, the client records the actual token usage and returns the result to the agent.

---

## 7. Testing & Backtests

*   **Unit Tests**: Each client will be tested against a mocked API backend (`httpx-mock`) to verify that it correctly handles success, transient errors, and fatal errors. The `budget_meter` and `guardrails` will have their own focused unit tests.
*   **Backtesting**: The `verifier` can use the `budget_ledger.sqlite` database to perform an audit. It can sum the token usage recorded in the ledger for a given session and compare it against the total budget allocated for that session, verifying that the budget meter worked correctly.

---

## 8. Security & Policy

This directory is a primary security boundary for interactions with the outside world.

*   **Guardrails**: `guardrails.py` is the primary enforcer of security policies related to data exfiltration and prompt injection. It ensures that no sensitive data is sent to third-party LLMs and that the LLMs are not manipulated into performing unsafe actions.
*   **Authentication**: Each client is responsible for securely loading and using its API key from the environment, ensuring these secrets are never logged or exposed.
*   **Egress Control**: The clients will respect the global "local-only" mode, refusing to make any network calls if it is enabled.

---

## 9. Readme Cross-Reference

The `llm_clients/` directory provides the sophisticated "thinking" tools that the agents in the `README.md`'s puzzle-solving framework use.

| LLM Client Component | README.md Concept Cross-Reference |
| :--- | :--- |
| **LLM Clients** | When the puzzle solver is faced with a particularly complex gap that requires creativity or deep reasoning (not just deterministic checks), it can "ask for help" from a super-intelligent external expert. The LLM clients are the secure telephone line to that expert. |
| **Budget Meter** | Represents the cost of asking the expert for help. The solver knows it can't call the expert for every single piece; it must use this expensive resource wisely, which is why the `Planner`'s priority formula is so important. |
| **Guardrails** | The set of rules the solver follows when talking to the expert, ensuring it doesn't accidentally reveal sensitive information about the puzzle's owner or ask the expert to do something dangerous. |

This directory allows pForge to leverage the power of modern LLMs without sacrificing its principles of safety, verifiability, and economic discipline.
