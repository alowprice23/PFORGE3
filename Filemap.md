# pForge File Map

This document provides a high-level overview of the key directories and files in the pForge project.

## Core Directories

*   **`pforge/`**: The main source code for the pForge application.
    *   **`agents/`**: Contains the implementations of the specialized AI agents (`ObserverAgent`, `PlannerAgent`, `FixerAgent`, etc.). This is the brain of the system.
    *   **`cli/`**: Contains the command-line interface logic, built with Typer. This is the primary user interface.
    *   **`llm_clients/`**: Provides clients for interacting with external Large Language Models (e.g., OpenAI).
    *   **`messaging/`**: Contains the in-memory message bus for agent communication.
    *   **`validation/`**: Contains tools for validating code, including the test runner (`test_runner.py`) that is central to the test-driven workflow.
    *   **`proof/`**: Contains logic for creating and managing `ProofBundle` objects, which are verifiable records of the system's operations.
*   **`tests/`**: Contains the automated tests for the pForge system.
    *   **`unit/`**: Unit tests for individual components.
    *   **`integration/`**: Tests for the interaction between components.
    *   **`e2e/`**: End-to-end tests that run the entire application workflow.

## Key Files

*   **`README.md`**: This file. Provides a high-level overview of the project.
*   **`pforge/cli/main.py`**: The entry point for the `pforge` command-line application.
*   **`pforge/cli/skills/doctor.py`**: Implements the `doctor` command, which launches the main agent workflow.
*   **`pforge/messaging/in_memory_bus.py`**: The simple, `asyncio.Queue`-based message bus used for inter-agent communication.
*   **`pforge/agents/observer_agent.py`**: The agent responsible for running tests and detecting failures.
*   **`pforge/agents/planner_agent.py`**: The agent responsible for creating repair plans based on test failures.
*   **`pforge/agents/fixer_agent.py`**: The agent responsible for applying patches and verifying their correctness.
*   **`pforge/validation/test_runner.py`**: The utility used by the agents to run tests and get structured results.
*   **`pforge/tests/e2e/test_doctor_command.py`**: The end-to-end test that simulates a real repair scenario and validates the entire agent workflow.

## Documentation

*   **`PLAN.md` files**: Each major directory contains a `PLAN.md` file that outlines the development goals and status for that specific component of the project.
