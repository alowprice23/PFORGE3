# PLAN: `config/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `config/` directory is the single source of truth for all static, declarative configuration of the pForge system. It allows operators and developers to tune the system's behavior, set resource limits, define security policies, and manage external integrations without modifying source code. This separation of configuration from code is a critical design principle that enhances security, maintainability, and operational flexibility.

**Scope of Ownership**:

*   **System Settings**: It owns `settings.yaml`, which controls global operational parameters like ports, feature flags, and the mathematical constants for the efficiency formula.
*   **LLM Provider Configuration**: It owns `llm_providers.yaml`, which defines the endpoints, models, and cost structures for all supported Large Language Models (Gemini, Claude, OpenAI).
*   **Agent Configuration**: It owns `agents.yaml`, which governs the behavior of the agent swarm, including which agents are enabled and their operational parameters (spawn weights, retry bounds).
*   **Resource Quotas**: It owns `quotas.yaml`, which defines the resource limits (CPU, memory, tokens) for the system, with support for per-tenant overrides.
*   **Security Policies**: It owns the security-related configurations, including `seccomp.json` for hardening shell execution, `allowlists.yaml` for command and network egress control, and `policies.yaml` for defining the system's gating and safety policies.

**Explicitly Not in Scope**:

*   **Dynamic State**: This directory contains no dynamic or runtime state. That is managed by the `orchestrator/` and stored in `var/`.
*   **Business Logic**: The `config/` directory does not contain any code. It only contains data files (YAML, JSON). All logic for parsing and applying these configurations resides in the `pforge/` application source code.
*   **Secrets**: This directory does not contain secrets. Secrets are managed through environment variables or a secure vault, as defined in `.env.example`.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `settings.yaml` [x]

*   **Responsibilities**: To provide global settings for the pForge system.
    *   `service`: Defines the service name, environment (dev/prod), and log level.
    *   `ports`: Defines the default ports for all services (API, UI, Grafana, etc.).
    *   `feature_flags`: A set of booleans to enable or disable major features (e.g., `enable_metrics`, `enable_agent_economy`).
    *   `formula_constants`: The tunable weights (γ, α, λ, β, η, θ, δ) for the `E_intelligent` formula.
*   **Interfaces**: Parsed by `pforge/settings.py` and made available to the entire application.

### 2.2. `llm_providers.yaml` [x]

*   **Responsibilities**: To define the connection and cost parameters for all supported LLMs. Each entry contains:
    *   `provider`: The name of the provider (e.g., "openai").
    *   `model`: The specific model name (e.g., "gpt-4o-mini").
    *   `endpoint`: The API endpoint URL.
    *   `max_context_tokens`: The maximum context window size.
    *   `cost_per_1k_tokens`: The cost for prompt and completion tokens, used for budget management.
    *   `default_temperature`: The default sampling temperature.
*   **Interfaces**: Used by `llm_clients/` to instantiate the correct client with the correct parameters.

### 2.3. `agents.yaml` [x]

*   **Responsibilities**: To configure the behavior of the agent swarm. Each agent has an entry with:
    *   `weight`: The agent's utility weight in the scheduler.
    *   `spawn_threshold`: The utility score required to spawn the agent.
    *   `retire_threshold`: The utility score below which the agent will be retired.
    *   `max_tokens_tick`: The maximum number of tokens the agent can consume in a single tick.
*   **Interfaces**: Used by `orchestrator/scheduler.py` to make decisions about the agent lifecycle.

### 2.4. `quotas.yaml` [x]

*   **Responsibilities**: To define resource quotas for the system.
    *   `defaults`: The default quotas for all tenants.
    *   `tenants`: A list of tenant-specific overrides.
    *   Quotas include `max_tokens_per_day`, `cpu_limit`, `memory_soft`, `shell_execs_per_min`, etc.
*   **Interfaces**: Used by `server/middleware/budget_guard.py` and other resource management components.

### 2.5. `seccomp.json` [x]

*   **Responsibilities**: To define a hardened seccomp profile for the container that executes shell commands. It explicitly allows a minimal set of safe syscalls and denies all others.
*   **Security**: This is a critical security control that prevents container breakout and limits the blast radius of a compromised agent.
*   **Interfaces**: Used by the Docker/container runtime when starting the shell execution container.

### 2.6. `allowlists.yaml` [x]

*   **Responsibilities**: To define allowlists for shell commands and network egress.
    *   `shell`: A list of allowed commands and their permitted arguments.
    *   `network`: A list of allowed domains for outbound HTTP(S) requests.
*   **Security**: Prevents agents from executing arbitrary commands or making unauthorized network calls.
*   **Interfaces**: Used by the shell execution service and the LLM clients.

### 2.7. `policies.yaml` [x]

*   **Responsibilities**: To define the system's high-level operational policies.
    *   `gating_policy`: Defines which constraints (φ) are blocking for QED.
    *   `qed_window`: The stability window required before QED can be emitted.
    *   `cvar_alpha`: The α value for the CVaR calculation in the Planner.
*   **Interfaces**: Used by `orchestrator/qedsupervisor.py` and `planner/priority.py`.

---

## 3. Math & Guarantees (from README)

The `config/` directory is where the mathematical models are parameterized.

*   `formula_constants` in `settings.yaml` directly sets the weights in the `E_intelligent` formula.
*   `agents.yaml` provides the weights and thresholds that the `AdaptiveScheduler` uses to make its utility-based decisions.
*   `policies.yaml` defines the parameters for the CVaR calculation in the `Planner`, which is a key part of the risk-aware decision-making process.

The guarantee of this directory is that the system's behavior can be tuned and controlled in a predictable way by modifying these configuration files, without needing to change the underlying code.

---

## 4. Security & Policy

This directory is central to the security of the pForge system. `seccomp.json` and `allowlists.yaml` provide hard security boundaries, while `policies.yaml` defines the operational safety policies. The separation of these policies from the code allows for easy auditing and modification by security teams.
