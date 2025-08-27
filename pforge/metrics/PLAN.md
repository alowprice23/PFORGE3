# PLAN: `metrics/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `metrics/` directory provides the observability infrastructure for the pForge system. It is responsible for defining, collecting, and exposing the metrics that are used to monitor the system's health, performance, and progress. This directory is what makes the internal state of the pForge system visible and understandable to operators and developers.

**Scope of Ownership**:

*   **Metrics Definitions (`metrics_collector.py`)**: It owns the definitions of all the Prometheus gauges and counters that are used to monitor the system.
*   **Metrics Exposition (`prometheus_exporter.py`)**: It owns the implementation of the `/metrics` endpoint that exposes the metrics in the Prometheus text format.

**Explicitly Not in Scope**:

*   **Metrics Calculation**: This directory defines the metrics, but the logic for calculating them resides elsewhere (e.g., the `EfficiencyAnalystAgent` calculates the `E` and `H` values).
*   **Metrics Storage and Visualization**: This directory only exposes the metrics. The storage and visualization of the metrics is handled by external systems like Prometheus and Grafana.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `__init__.py` [x]

*   **Responsibilities**: To mark the `metrics/` directory as a Python package.

### 2.2. `metrics_collector.py` [x]

*   **Responsibilities**: To define all the Prometheus metrics for the system.
    *   It uses the `prometheus_client` library to define a set of gauges and counters for all the key metrics, including `pforge_efficiency`, `pforge_entropy`, `pforge_gaps`, etc.
    *   It provides a set of helper functions for updating the metrics from other parts of the system.
*   **Interfaces**: Used by the `EfficiencyAnalystAgent` and other components to update the metrics.

### 2.3. `prometheus_exporter.py` [x]

*   **Responsibilities**: To expose the metrics in the Prometheus text format.
    *   It provides a FastAPI router that implements the `/metrics` endpoint.
    *   It uses the `generate_latest` function from the `prometheus_client` library to generate the text-based exposition format.
*   **Interfaces**: The `/metrics` endpoint is scraped by a Prometheus server.

---

## 3. Math & Guarantees (from README)

The `metrics/` directory is the direct implementation of the "Quantify or It Didn't Happen" principle. It provides the concrete, measurable implementation of the mathematical objects that are central to the pForge system, such as the efficiency score `E` and the entropy `H`. The guarantee of this directory is that all the key performance indicators of the system will be exposed in a standard, reliable, and machine-readable format, allowing for the continuous monitoring and analysis of the system's behavior.
