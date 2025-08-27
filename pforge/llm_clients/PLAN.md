# PLAN: `llm_clients/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `llm_clients/` directory provides a unified, robust, and secure interface to all the external Large Language Models (LLMs) that pForge uses. It abstracts away the details of the individual provider APIs, provides a consistent interface for the agents, and enforces the system's policies on token budgeting, retries, and safety.

**Scope of Ownership**:

*   **Provider-Specific Clients (`gemini_client.py`, `claude_client.py`, `openai_o3_client.py`)**: It owns the implementation of the clients for each supported LLM provider.
*   **Retry Logic (`retry.py`)**: It owns the implementation of the exponential backoff and jitter retry logic that is used for all LLM API calls.
*   **Token Budgeting (`budget_meter.py`)**: It owns the client-side implementation of the token budget meter, which ensures that no agent can exceed its token quota.
*   **Safety Guardrails (`guardrails.py`)**: It owns the implementation of the safety guardrails that are applied to all LLM prompts and responses, such as refusing to process requests that contain secrets or would violate the system's egress policies.

**Explicitly Not in Scope**:

*   **Agent Logic**: This directory does not contain any agent logic. The agents are the clients of the services provided by this directory.
*   **Prompt Engineering**: The prompt templates are owned by the `cli/prompts/` directory. This directory only applies the safety guardrails to the prompts.
*   **Configuration**: The configuration for the LLM providers is owned by the `config/` directory.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `llm_clients/` directory as a Python package.

### 2.2. `gemini_client.py` [ ]

*   **Responsibilities**: To implement the client for the Google Gemini LLM.
    *   It wraps the Gemini SDK to provide a simple, high-level API for the agents.
    *   It includes logic for handling Gemini-specific error codes and for formatting prompts and responses in the way that Gemini expects.
*   **Interfaces**: Used by any agent that needs to use the Gemini model (e.g., the `PredictorAgent`).

### 2.3. `claude_client.py` [ ]

*   **Responsibilities**: To implement the client for the Anthropic Claude LLM.
    *   It wraps the Claude SDK.
    *   It handles Claude-specific error codes and prompt/response formatting.
*   **Interfaces**: Used by any agent that needs to use the Claude model (e.g., the `FixerAgent`).

### 2.4. `openai_o3_client.py` [ ]

*   **Responsibilities**: To implement the client for the OpenAI o3 LLM.
    *   It wraps the OpenAI SDK.
    *   It handles OpenAI-specific error codes and prompt/response formatting.
*   **Interfaces**: Used by any agent that needs to use the OpenAI o3 model (e.g., the `MisfitAgent`).

### 2.5. `retry.py` [ ]

*   **Responsibilities**: To provide a generic, robust retry mechanism for all LLM API calls.
    *   It uses the `tenacity` library to implement exponential backoff with jitter.
    *   It can be configured with different retry policies for different types of errors (e.g., transient network errors vs. rate limit errors).
*   **Interfaces**: Used as a decorator by all the LLM client methods.

### 2.6. `budget_meter.py` [ ]

*   **Responsibilities**: To enforce the token budget for each agent.
    *   It provides a `spend` method that an agent can call before making an LLM API call.
    *   The `spend` method checks if the agent has enough tokens left in its budget and raises an exception if not.
    *   It decrements the agent's budget after the API call is complete.
*   **Interfaces**: Used by all the LLM client methods.

### 2.7. `guardrails.py` [ ]

*   **Responsibilities**: To implement the safety guardrails for all LLM interactions.
    *   It provides a function to check a prompt for any secrets or other sensitive information before it is sent to the LLM.
    *   It provides a function to check a response from an LLM for any harmful or otherwise inappropriate content.
    *   It enforces the system's network egress policy, blocking any requests to unapproved domains.
*   **Security**: This is a critical security component that protects the system from malicious prompts and prevents the leakage of sensitive data.
*   **Interfaces**: Used by all the LLM client methods.

---

## 3. Math & Guarantees (from README)

The `llm_clients/` directory is a key part of the system's ability to make rational, economic decisions. The `budget_meter.py` is the direct implementation of the token budget constraints in the Planner's optimization problem. The retry logic in `retry.py` helps to ensure the reliability of the system, which is a prerequisite for the convergence of the optimization process. The `guardrails.py` are a key part of the safety constraints (Φ_safety).
