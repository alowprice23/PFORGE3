# PLAN: `cli/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `cli/` directory provides a powerful, interactive, and self-improving command-line interface for pForge, named `pforge`. This is not merely a set of wrappers around API endpoints; it is designed as an **agentic CLI**. It maintains its own memory, learns from the outcomes of its operations, and uses LLMs to plan and reason about complex workflows. It is the primary interface for expert users, automation scripts, and CI/CD integration.

**Scope of Ownership**:

*   **CLI Application Entry Point (`main.py`)**: It owns the main `pforge` command, built with a modern CLI framework like Typer, which serves as the entry point for all subcommands.
*   **Conversational Interface (`chat.py`)**: It owns the interactive REPL (Read-Eval-Print Loop) that allows users to "chat" with pForge, using natural language to trigger complex actions.
*   **Skill Implementation (`skills/`)**: It owns the concrete implementation of every discrete command or "skill" that the CLI can perform, from checking status to running a full diagnostic and repair cycle.
*   **Learned Memory and Routing (`routes/`)**: It manages the "constellation memory," a persistent database of past operations and their outcomes, and the registry of available skills. This is the foundation of its ability to learn and improve.
*   **LLM Prompting (`prompts/`)**: It owns the curated, versioned prompt templates that are used to guide the LLM for planning, summarization, and safety-guarded code generation.

**Explicitly Not in Scope**:

*   **Core Backend Logic**: The CLI is a **client**. It does not implement the puzzle-solving logic, the agent orchestration, or the proof verification. It consumes the APIs provided by the `server/` and uses the Python APIs of other backend modules.
*   **Web UI**: It is a terminal-based interface and has no direct connection to the `ui/` React application, although both interact with the same backend.
*   **Direct Database/Storage Manipulation**: While it uses the constellation SQLite database, it does so through the `memory/` abstraction layer. It does not contain raw SQL or direct CAS manipulation logic.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `cli/` directory as a Python package.

### 2.2. `main.py` [x]

*   **Responsibilities**:
    *   To be the executable entry point for the `pforge` command (configured in `pyproject.toml`).
    *   To use `Typer` to initialize the main application and dynamically discover and register all subcommands (skills) from the `skills/` directory.
    *   To launch the interactive chat loop (`chat.py`) if `pforge` is run without a subcommand.
*   **Tests**: Tested via end-to-end CLI tests that invoke the compiled `pforge` command.

### 2.3. `chat.py` [ ]

*   **Responsibilities**:
    *   To implement the conversational REPL.
    *   To take raw user input, send it to the backend `IntentRouterAgent` (via the `/chat/nl` API endpoint), and receive a structured intent in response.
    *   To map the returned intent to the execution of one or more skills from the `skills/` directory.
    *   To manage the display of the conversation, distinguishing between user input, pForge responses, and logs from backend operations.
*   **Algorithms**: The core logic is a loop that reads input, makes an API call, and dispatches to a skill based on the response.
*   **Tests**: A `test_chat.py` will use a mock API to test the intent-to-skill mapping logic for various simulated user inputs.

### 2.4. `routes/` Subdirectory [ ]

This directory manages the CLI's knowledge of its own capabilities and history.

*   **`registry.yaml`**: A static YAML file that defines all available skills. This provides a structured "tool manifest" that can be passed to the planning LLM, allowing it to reason about which commands are available and what their parameters are. Example entry:
    ```yaml
    - name: doctor
      description: "Run a full diagnostic and repair cycle on a target directory."
      params:
        - name: target_path
          type: str
          required: false
          default: "."
    ```
*   **`learned.sqlite`**: This is not a source file, but a placeholder for the path to the constellation memory database. The plan for this database is defined by `storage/sqlite/constellation_schema.sql`. The CLI interacts with it via the `memory/constellation.py` module.

### 2.5. `skills/` Subdirectory

This directory contains the implementation of each subcommand. Each `.py` file corresponds to a `pforge` subcommand.

*   **`status.py` [ ]**: Implements `pforge status`. It calls the `/metrics` endpoint and other status endpoints on the backend and formats the response into a human-readable summary of the system's health (E, H, agent status, etc.).
*   **`doctor.py` [~]**: Implements the `pforge doctor` command. This is the primary agentic loop of the CLI. It repeatedly senses the state, uses the learning policy (`agentic/policy.py`) to choose the next best skill, executes it, and records the outcome in the constellation memory, continuing until the system reaches a QED state.
*   **`preflight.py` [ ]**: Implements `pforge preflight`. Triggers the backend `RecoveryAgent` to run its prerequisite checks and displays the results.
*   **`fix.py` [ ]**: Implements `pforge fix`. A lower-level command to apply a specific patch or run a specific `Fixer` task.
*   **`verify.py` [ ]**: Implements `pforge verify`. A wrapper around the `proof/backtest_cli.py` to run a full audit on a past session.
*   **`routes.py` [ ]**: Implements `pforge routes`. Provides commands to inspect the constellation memory, showing the most effective learned routes for different contexts.
*   **`proofs.py` [ ]**: Implements `pforge proofs`. Fetches and displays formatted proof bundles from the backend.
*   **`budget.py` [ ]**: Implements `pforge budget`. Allows the user to view and, if authorized, adjust the token budgets for the LLM clients.

### 2.6. `prompts/` Subdirectory

This directory holds the version-controlled prompt templates that guide the CLI's LLM interactions.

*   **`system_puzzle.md`**: The master system prompt that frames all tasks for the planning LLM within the puzzle-solving mathematics. It instructs the LLM to think in terms of E, H, Φ, P, etc.
*   **`fixer_guard.md`**: A safety-focused prompt fragment that is prepended to any request sent to an LLM for code generation. It contains negative constraints, e.g., "DO NOT output anything other than a unified diff. DO NOT use unsafe libraries."
*   **`router_guard.md`**: A prompt used by the `chat.py` intent parser to help it decide whether a user's request pertains to a single file or a whole directory, helping it choose the right skill or parameters.
*   **`summarizer_style.md`**: A prompt that instructs a summarization LLM to be terse, verifiable, and to ground its explanations in the data from a proof bundle.

---

## 3. Math & Guarantees (from README)

The `cli/` is the primary implementation of the **learning and adaptation** components of the mathematical framework.

*   **Reinforcement Learning**: The `doctor` skill's loop is a direct implementation of a reinforcement learning agent. It exists in a `context` (derived from Σ), takes an `action` (a skill), and receives a `reward` (`R = αΔE + ...`). This guarantees that the CLI's behavior is not static but demonstrably improves over time.
*   **UCB1/Thompson Sampling**: The policy for choosing the next action is based on a sound mathematical algorithm for balancing exploration (trying new skills) and exploitation (using skills that have worked well in the past). This is implemented in `agentic/policy.py` and used by `doctor.py`.
*   **Constellation Memory**: The `routes/learned.sqlite` database provides a persistent, mathematical record of the system's experience, allowing it to build a map of high-reward paths through the problem space.

---

## 4. Routing & Awareness

The CLI is designed to be highly aware.

*   **Self-Awareness**: It is aware of its own capabilities (`routes/registry.yaml`), its own performance history (`routes/learned.sqlite`), and the state of the backend system (`skills/status.py`).
*   **Intent Routing**: `chat.py` routes natural language to specific, executable skills.
*   **Workflow Routing**: The `doctor` skill uses its learned policy to route its own sequence of actions, creating intelligent, multi-step workflows automatically.

---

## 5. Token & Budget Hygiene

The `skills/budget.py` command provides a direct user interface for monitoring and managing budgets. The agentic parts of the CLI that use LLMs (e.g., for planning in `chat.py`) are themselves clients of the `llm_clients/` and respect all budget constraints, refusing to act if the budget is exhausted.

---

## 6. Operational Flows

*   **Agentic `doctor` Flow**:
    1.  User runs `pforge doctor`.
    2.  The `doctor.py` skill starts its main loop.
    3.  It calls `status.py` to get the current state (context).
    4.  It queries the constellation memory for the best action in that context, using its UCB1 policy.
    5.  Let's say the policy chooses the `preflight` skill. It executes `preflight.py`.
    6.  It gets the result (a proof from the `RecoveryAgent`). It measures the `ΔE` and `Δtests_passed`.
    7.  It computes the reward `R` and records the `(context, action, reward)` tuple in the constellation database.
    8.  It repeats the loop, now with an updated context, until the `status.py` skill reports a QED state.

---

## 7. Testing & Backtests

*   **Unit Tests**: Each skill will have unit tests that mock its backend dependencies and verify its logic. The learning policy in `agentic/policy.py` will be tested with synthetic reward data.
*   **Integration Tests**: The CLI will be tested using a library like `Typer`'s own testing tools, which can invoke the command and capture its output.
*   **End-to-End Tests**: An e2e test will run `pforge doctor` on the `demo_buggy/` project and assert that it successfully completes the repair and that the constellation database contains a record of the actions taken.

---

## 8. Security & Policy

*   **Skill Allowlist**: The CLI's primary security mechanism is that it does not execute arbitrary shell commands. It only executes registered, validated Python modules from the `skills/` directory. This prevents a user (or a manipulated LLM) from tricking it into running `rm -rf /`.
*   **Guardrail Prompts**: The prompts in the `prompts/` directory are a critical security control, instructing the LLMs to stay within safe operational boundaries.
*   **Privacy**: The CLI must use the `utils/privacy_filters.py` to scrub any context (like file paths or code snippets) before sending it to an external LLM for planning.

---

## 9. Readme Cross-Reference

The agentic CLI is the ultimate embodiment of the "intelligent solver" from the `README.md`.

| CLI Component | README.md Concept Cross-Reference |
| :--- | :--- |
| **`doctor` Skill** | The main puzzle-solving process, which iteratively tries moves, learns from the outcomes, and works towards a completed state. |
| **Constellation Memory** | The solver's memory of which "sequences of moves" (Π) have been successful in the past, allowing it to get better with experience. |
| **`chat.py`** | The "conversation interface" that allows a human to collaborate with, guide, and query the solver. |
| **`skills/`** | The set of discrete "moves" or "abilities" that the solver has at its disposal (e.g., "check for misfits," "place a piece," "verify a section"). |

This directory transforms pForge from a passive backend into an active, learning partner for the developer.
