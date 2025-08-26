# PLAN: `config/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `config/` directory provides a centralized, version-controlled, and human-readable location for all of the pForge system's operational configuration. By externalizing these parameters from the application code, this directory allows for easy tuning, environment-specific overrides, and clear management of all runtime behaviors. It is the system's control panel, defined as data.

**Scope of Ownership**:

*   **Application Settings (`settings.yaml`)**: It owns the global settings like ports, feature flags, and operational modes.
*   **LLM Provider Configuration (`llm_providers.yaml`)**: It owns the detailed configuration for all supported Large Language Models, including their endpoints, costs, and default parameters.
*   **Agent Behavior (`agents.yaml`)**: It owns the configuration that governs the agent economy, such as which agents are enabled and their spawn/retire thresholds.
*   **Resource Management (`quotas.yaml`)**: It owns the definitions for resource quotas (tokens, CPU, memory) for the system and for individual tenants.
*   **Security Profiles (`seccomp.json`, `allowlists.yaml`)**: It owns the data files that define key security boundaries, such as the allowed system calls and shell commands.
*   **Policy Parameters (`policies.yaml`)**: It owns the tunable parameters for the system's core mathematical and logical policies, such as the efficiency target for the QED gate.

**Explicitly Not in Scope**:

*   **Configuration-Consuming Logic**: This directory contains only the data files. The Python code that loads, parses, and uses this configuration resides in other modules (e.g., `pforge/settings.py`, `orchestrator/scheduler.py`).
*   **Security Policy Definitions**: While it contains parameters for policies, the core definitions (like redaction regexes or public keys) belong in the `policies/` directory.
*   **Environment Secrets**: It does not contain secrets like API keys. It is designed to be safely checked into version control. Secrets are provided via the `.env` file or a secure vault.

---

## 2. File-by-File Blueprints

### 2.1. `settings.yaml`

*   **Purpose**: To define global, application-wide settings.
*   **Schema**:
    *   `service`: Contains metadata like `name` and `environment` (`dev`, `staging`, `prod`).
    *   `ports`: Defines the default network ports for the API, UI, Grafana, etc.
    *   `feature_flags`: A set of booleans to enable or disable major features (e.g., `enable_agent_economy`, `enable_telemetry`).
    *   `mode`: The default operational mode, e.g., `local` (uses `fakeredis`) or `docker`.
    *   `cadence`: The default tick interval for the orchestrator loop in seconds.

### 2.2. `llm_providers.yaml`

*   **Purpose**: To centralize the configuration for all external LLM providers.
*   **Schema**: A list of provider objects. Each object contains:
    *   `name`: A unique identifier (e.g., `openai_o3_fixer`).
    *   `provider`: The vendor (e.g., `openai`, `anthropic`, `google`).
    *   `model`: The specific model name (e.g., `gpt-4o-mini`, `claude-3.7-sonnet-20250515`).
    *   `endpoint`: The API endpoint URL.
    *   `max_context_tokens`: The model's context window size.
    *   `cost_per_1k_tokens`: An object with `prompt` and `completion` costs in USD.
    *   `default_params`: Default generation parameters like `temperature`.

### 2.3. `agents.yaml`

*   **Purpose**: To configure the behavior of the agent swarm and the adaptive economy.
*   **Schema**: A list of agent configuration objects. Each object contains:
    *   `name`: The name of the agent (e.g., `fixer`, `predictor`).
    *   `enabled`: A boolean to enable or disable the agent.
    *   `spawn_weight`: The agent's weight in the scheduler's utility function.
    *   `spawn_threshold`, `retire_threshold`: The utility scores that trigger a state change.
    *   `max_concurrency`: The maximum number of instances of this agent type that can run in parallel.

### 2.4. `quotas.yaml`

*   **Purpose**: To define resource limits to control costs and prevent abuse.
*   **Schema**:
    *   `defaults`: A section defining the default quotas for any tenant.
        *   `max_tokens_per_day`: Global and per-vendor token limits.
        *   `cpu_limit`, `memory_limit`: Default resource limits for containerized environments.
    *   `tenants`: An optional list of objects for per-tenant overrides, allowing for different service tiers.

### 2.5. `seccomp.json`

*   **Purpose**: To provide a hardened security profile for containers, drastically reducing the kernel's attack surface.
*   **Format**: A standard seccomp-bpf JSON profile. It will have a `defaultAction` of `SCMP_ACT_ERRNO` (deny by default) and an explicit `syscalls` list of allowed system calls (e.g., `read`, `write`, `exit`, but not `ptrace` or `mount`).

### 2.6. `allowlists.yaml`

*   **Purpose**: To define explicit allowlists for potentially dangerous operations.
*   **Schema**:
    *   `shell_commands`: A list of exact commands that the `test_runner` or other shell-executing components are allowed to run (e.g., `["pytest", "npm", "black"]`). Any other command will be blocked.
    *   `egress_domains`: A list of domain names that the system is allowed to connect to when not in `local-only` mode (e.g., `api.openai.com`, `api.anthropic.com`).

### 2.7. `policies.yaml`

*   **Purpose**: To externalize the tunable parameters of the system's core mathematical and logical policies.
*   **Schema**:
    *   `qed_gate`:
        *   `efficiency_target`: The target `E*` value required for QED.
        *   `stability_window_ticks`: The number of ticks `E` must remain stable.
    *   `planner`:
        *   `cvar_alpha`: The alpha value (e.g., `0.90`) for the CVaR calculation, controlling risk aversion.
    *   `constraints`:
        *   A list of `φ_i` IDs and their `blocking` status (`true` or `false`). This allows an operator to downgrade a failing structural constraint to non-blocking to allow progress.

---

## 3. Math & Guarantees (from README)

This directory provides the guarantee of **Configurability and Transparency** for the mathematical framework.

*   The tunable parameters of the core formulas (`E`, `P_cvar`) are not magic numbers hidden in the code; they are explicitly defined in `policies.yaml`.
*   This allows operators to adjust the system's "risk appetite" (`cvar_alpha`) or its definition of "done" (`efficiency_target`) to suit different projects or goals.
*   This transparency makes the system's behavior auditable and its results reproducible, given the same configuration.

---

## 4. Routing & Awareness

This directory provides **Configuration Awareness**. A central settings module (`pforge/settings.py`) loads all these files at startup into a single, type-safe configuration object. This object is then made available throughout the application (e.g., via dependency injection), ensuring that every component is aware of and respects the current system-wide configuration.

---

## 5. Token & Budget Hygiene

`llm_providers.yaml` and `quotas.yaml` are the cornerstones of budget hygiene. The first provides the cost data, and the second provides the spending limits. The `llm_clients/budget_meter.py` consumes this configuration to enforce the financial policies of the system in real-time.

---

## 6. Operational Flows

*   **Application Startup Flow**:
    1.  `pforge` application starts.
    2.  `pforge/settings.py` is initialized.
    3.  It loads the default values from all files in the `config/` directory.
    4.  It overrides these defaults with any values found in environment variables (e.g., `PFORGE_MODE=local`).
    5.  The final, immutable configuration object is created and used to initialize all other major components like the `Orchestrator` and the agent clients.

---

## 7. Testing & Backtests

*   The primary testing strategy for this directory is **schema validation**. A dedicated test will ensure that all default `.yaml` and `.json` files can be parsed correctly and conform to their expected Pydantic models.
*   The unit tests for other modules will load test-specific versions of these config files to verify that the modules correctly adapt their behavior based on the configuration provided.

---

## 8. Security & Policy

This directory is a critical component of the system's security posture.

*   **Security as Code/Data**: `seccomp.json` and `allowlists.yaml` turn security policies into auditable data, which is a security best practice.
*   **Preventing Misconfiguration**: By centralizing configuration, it reduces the risk of developers hardcoding settings or secrets in multiple places.
*   **Access Control**: In a production environment, the files in this directory should have restricted write access to prevent unauthorized changes to the system's behavior or security boundaries.

---

## 9. Readme Cross-Reference

This directory contains the "tuning knobs" and "dials" for the puzzle-solving machine from the `README.md`.

| Config File | README.md Concept Cross-Reference |
| :--- | :--- |
| `policies.yaml` | Allows the user to adjust the solver's "personality"—is it more risk-averse (`cvar_alpha`)? What is its definition of a "solved" puzzle (`efficiency_target`)? |
| `agents.yaml` | Allows the user to turn certain "specialist solvers" (agents) on or off, or to adjust how eagerly they are brought in to help. |
| `quotas.yaml` | Represents the hard limits on the solver's resources, like "you only have one hour" (time budget) or "you can only ask the expert for help five times" (token budget). |

This directory makes the system's behavior transparent and gives the operator fine-grained control over its strategy.
