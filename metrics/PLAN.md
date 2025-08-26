# PLAN: `metrics/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `metrics/` directory provides a centralized, standardized way of defining, collecting, and exposing all system metrics for observability. It serves as the single source of truth for what is being measured in the pForge system and provides the interface for monitoring tools like Prometheus. Its purpose is to make the internal state and performance of the complex, multi-agent system transparent and queryable in real-time.

**Scope of Ownership**:

*   **Metric Definitions (`metrics_collector.py`)**: It owns the canonical definition of every Prometheus metric used in the system. This includes Counters for tracking totals (e.g., ticks, errors), Gauges for tracking current values (e.g., efficiency, active agents), and Histograms for tracking distributions (e.g., tick duration).
*   **Global Metric Registry**: It provides a centralized registry of these metric objects, ensuring that all components of the system are updating the exact same metric objects, preventing fragmentation and naming inconsistencies.
*   **Prometheus Exporter (`prometheus_exporter.py`)**: It owns the FastAPI router that exposes the `/metrics` endpoint, which serves the collected metrics in the Prometheus text-based exposition format.

**Explicitly Not in Scope**:

*   **Metric Calculation**: This directory does not *calculate* the values of the metrics. The logic for calculating efficiency, entropy, etc., resides in the `orchestrator/efficiency_engine.py` and various agents. This directory only provides the `Gauge` or `Counter` objects that those components import and update.
*   **The Monitoring Stack**: It does not own the Prometheus server, Grafana, or any alerting infrastructure. It is a data source that these external tools consume.
*   **Logging and Tracing**: This directory is focused exclusively on time-series metrics. It is not responsible for structured logging or distributed tracing, which are separate observability concerns.

---

## 2. File-by-File Blueprints

### 2.1. `__init__.py`

*   **Responsibilities**: To mark the `metrics/` directory as a Python package.

### 2.2. `metrics_collector.py`

*   **Responsibilities**:
    *   To instantiate and export every Prometheus metric object used in the application. This is the single place where metric names, descriptions, and labels are defined.
    *   To group related metrics for clarity (e.g., Efficiency Metrics, Agent Metrics, Budget Metrics).
    *   To provide optional high-level helper functions, like `update_state_gauges(state: PuzzleState)`, which takes a state object and updates a whole set of related gauges at once (e.g., efficiency, entropy, gaps, misfits). This simplifies the code in the consuming modules.
*   **Data Models**: This module consists entirely of `prometheus_client` objects (`Counter`, `Gauge`, `Histogram`). Examples:
    ```python
    # In metrics_collector.py
    from prometheus_client import Gauge, Counter

    PFORGE_EFFICIENCY = Gauge("pforge_efficiency", "Global puzzle efficiency score (E)")
    PFORGE_ENTROPY = Gauge("pforge_entropy", "System entropy score (H)")
    PFORGE_AGENTS_ACTIVE = Gauge("pforge_agents_active", "Number of active agents", ["agent_type"])
    PFORGE_TOKENS_USED_TOTAL = Counter("pforge_tokens_used_total", "Tokens used", ["vendor"])
    ```
*   **Tests**: A `test_metrics_collector.py` will import the module and check that all expected metric objects exist and have the correct type and label configurations.

### 2.3. `prometheus_exporter.py`

*   **Responsibilities**:
    *   To define a FastAPI `APIRouter`.
    *   To create a `GET /metrics` endpoint.
    *   The endpoint handler will call `prometheus_client.generate_latest()` to collect the current state of all registered metrics from the default registry.
    *   To return this data in an HTTP `Response` with the correct `Content-Type` header (`text/plain; version=0.0.4`).
*   **Data Models**: None.
*   **Algorithms**: None. It's a simple wrapper around the `prometheus-client` library function.
*   **Tests**: An integration test `test_prometheus_exporter.py` will use FastAPI's `TestClient`. The test will:
    1.  Import a metric object from `metrics_collector.py` and set its value (e.g., `PFORGE_EFFICIENCY.set(1.23)`).
    2.  Make a request to the `/metrics` endpoint via the `TestClient`.
    3.  Assert that the response status code is 200 and that the response body contains the string `pforge_efficiency 1.23`.

---

## 3. Math & Guarantees (from README)

This directory provides the guarantee of **Measurability**. It is the direct, real-time implementation of the observability for the core mathematical constructs of the pForge system.

*   **`E` and `H` as Gauges**: The `pforge_efficiency` and `pforge_entropy` gauges provide a live, queryable view into the system's core objective functions. This makes the abstract mathematical state of the system concrete and observable.
*   **Proof of Progress**: The time-series data generated by this directory is the primary data source for verifying that the system is making progress (`ΔE > 0`). It provides the ground truth for backtesting the effectiveness of the `Planner`'s decisions.

---

## 4. Routing & Awareness

This directory provides **Performance Awareness** to external monitoring systems. By scraping the `/metrics` endpoint, tools like Prometheus become "aware" of the internal state of pForge without needing to understand its complex architecture. This enables:

*   **Automated Alerting**: Setting up alerts for conditions like a sustained drop in efficiency, a spike in agent errors, or a critically low token budget.
*   **Dashboarding**: Creating dashboards in Grafana to visualize the health and performance of the system over time.

---

## 5. Token & Budget Hygiene

This directory is essential for budget hygiene. The `PFORGE_TOKENS_USED_TOTAL` counter, defined in `metrics_collector.py`, is the authoritative source for real-time data on token consumption. This metric is used by:

*   The `llm_clients/budget_meter.py` to make enforcement decisions.
*   The `server/` and `ui/` to display budget information to the user.
*   External alerting systems to warn operators of potential cost overruns.

---

## 6. Operational Flows

*   **An Agent Updates a Metric**:
    1.  The `FixerAgent` successfully applies a patch.
    2.  It imports the `PATCHES_APPLIED` counter from `metrics_collector.py`.
    3.  It calls `PATCHES_APPLIED.inc()`. The `prometheus-client` library handles the thread-safe update of the metric's value in memory.
*   **Prometheus Scrapes the Endpoint**:
    1.  An external Prometheus server, following its configuration, sends a `GET` request to `http://pforge-server:8000/metrics`.
    2.  The request is handled by the router in `prometheus_exporter.py`.
    3.  The handler calls `generate_latest()`, which gathers the current values of all defined metrics, including the newly incremented `PATCHES_APPLIED` counter.
    4.  The formatted text response is sent back to Prometheus, which stores it in its time-series database.

---

## 7. Testing & Backtests

*   **Unit and Integration Tests**: As described in the blueprints, the tests will ensure the metrics are defined correctly and the endpoint serves them in the proper format.
*   **Backtesting**: The metrics are the **primary output** used in backtesting. A `verifier` script can analyze the historical time-series data for metrics like `pforge_efficiency` and correlate it with the log of `PLAN.PROPOSED` events to determine if the planner's decisions were effective. High-priority plans should, on average, lead to a larger positive `ΔE`.

---

## 8. Security & Policy

The `/metrics` endpoint exposes detailed internal operational data. While it should not expose secrets, the data could still be sensitive from a performance or business perspective. Therefore, in a production environment, the endpoint must be protected. The plan is to have the `server/app.py` mount the metrics router behind the `auth` middleware, ensuring that only authenticated clients (like the Prometheus server) can scrape the metrics.

---

## 9. Readme Cross-Reference

This directory provides the implementation of the "scoreboard" for the puzzle-solving framework described in the `README.md`.

| Metrics Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `pforge_efficiency` Gauge | The real-time display of the `E_intelligent(Σ)` score. It's the most direct measure of whether the system is "winning" the puzzle. |
| `pforge_entropy` Gauge | The real-time display of the `H(Σ)` score, quantifying the "messiness" or "disorder" of the puzzle state. |
| `pforge_gaps`, `pforge_misfits` Gauges | The live counts of the `E(t)` and `M(t)` terms from the formula—the number of empty spaces and wrongly placed pieces. |

This directory makes the abstract mathematical model of the system's health concrete, observable, and actionable.
