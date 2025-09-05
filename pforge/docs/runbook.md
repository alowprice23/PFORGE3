# pForge Operational Runbook

This document provides instructions for deploying, operating, and troubleshooting the pForge system.

## 1. Deployment

pForge is designed to be "local-first," but it also supports a Docker-based deployment for a more isolated environment.

### 1.1. Local (Non-Docker) Deployment

This is the recommended method for local development and usage.

**Prerequisites**:

*   Python 3.11+
*   Node.js 20+

**Steps**:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/alowprice23/PFORGE.git
    cd PFORGE
    ```
2.  **Set up the environment and install dependencies**:
    The `pforge/scripts/local_boot.sh` script automates this process.
    ```bash
    bash pforge/scripts/local_boot.sh
    ```
    This will:
    *   Create a Python virtual environment at `.venv`.
    *   Install the required Python dependencies from `pforge/requirements.txt`.
    *   (Optionally) Install Node.js dependencies for the UI.
    *   (Optionally) Start the Uvicorn server for the API and the Vite server for the UI.

3.  **Start the system**:
    If you didn't use the `local_boot.sh` script to start the servers, you can do so manually:
    *   **API Server**:
        ```bash
        source .venv/bin/activate
        uvicorn pforge.server.app:app --reload
        ```
    *   **UI Server**:
        ```bash
        npm run --prefix pforge/ui dev
        ```

### 1.2. Docker-Based Deployment

For a more isolated environment, you can use Docker and Docker Compose.

**Prerequisites**:

*   Docker
*   Docker Compose

**Steps**:

1.  **Run the bootstrap script**:
    The `pforge/scripts/bootstrap.sh` script automates the process of building and starting the Docker containers.
    ```bash
    bash pforge/scripts/bootstrap.sh
    ```
    This will:
    *   Build the Docker images for the orchestrator and UI.
    *   Start all services defined in `docker-compose.yml` (including Redis, Neo4j, etc.).
    *   (Optionally) Seed the system with a sample repository.

2.  **Access the system**:
    *   **UI**: `http://localhost:8080`
    *   **API**: `http://localhost:8000`

## 2. Configuration

The primary configuration for the pForge system is located in the `pforge/config` directory.

*   **`settings.yaml`**: The main configuration file. It controls service settings, ports, feature flags, and the cadence of the orchestrator's event loop.
*   **`agents.yaml`**: Defines which agents are enabled, their spawn weights, and retry bounds.
*   **`llm_providers.yaml`**: Contains settings for the different Large Language Model (LLM) providers, such as model names, API endpoints, and costs.
*   **`policies.yaml`**: Governs the behavior of the system, such as which constraints are blocking and the stability window for the QED (Quod Erat Demonstrandum) completion predicate.
*   **`allowlists.yaml`**: Contains allowlists for shell commands and network egress domains.

## 3. Operations

### 3.1. Starting and Stopping the System

*   **Local**:
    *   **Start**: Use the `pforge/scripts/local_boot.sh` script or start the Uvicorn and Vite servers manually.
    *   **Stop**: Use `Ctrl+C` to stop the servers.
*   **Docker**:
    *   **Start**: `docker compose up -d`
    *   **Stop**: `docker compose down`

### 3.2. Monitoring

*   **Health Check**: The `GET /api/healthz` endpoint can be used to check if the API server is running.
*   **Metrics**: The `GET /metrics` endpoint provides Prometheus-compatible metrics for monitoring the system's performance and health.
*   **Logs**: The system logs to standard output. In a Docker-based deployment, you can view logs using `docker compose logs`.

## 4. Troubleshooting & Recovery

pForge includes a sophisticated preflight and recovery system to handle common environmental issues.

### 4.1. Preflight Checks

Before attempting any code analysis or modification, pForge runs a series of preflight checks to ensure the environment is correctly configured. These checks are orchestrated by the `PreflightEngine` in `pforge/recovery/preflight.py`.

The preflight checks include:

*   **Runtime Versions**: Verifying that the correct versions of Python, Node.js, etc., are installed.
*   **Package Dependencies**: Ensuring that all required packages are installed and there are no version conflicts.
*   **Service Availability**: Checking that required services like Redis are running.
*   **Port Collisions**: Making sure that the ports required by the system are available.
*   **Timezone and Clock**: Detecting and correcting for non-deterministic behavior caused by time and timezone issues.

### 4.2. Recovery Actions

If a preflight check fails, the system will attempt to automatically remediate the issue using a corresponding recovery action. These actions are defined in the `pforge/recovery/actions` directory.

Examples of recovery actions include:

*   **`pkg_resolve`**: Installing or repairing package dependencies.
*   **`service_boot`**: Starting a required service (e.g., a fake Redis instance).
*   **`port_reassign`**: Finding a free port and reconfiguring the system to use it.
*   **`tz_set`**: Setting the timezone to UTC to ensure deterministic behavior.

If the system is unable to automatically remediate an issue, it will log an error and may require manual intervention. The preflight logs will provide detailed information about the failure and the attempted recovery actions.
