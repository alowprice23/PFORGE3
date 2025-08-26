# PLAN: `server/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `server/` directory provides the primary Application Programming Interface (API) and web service layer for the pForge system. It is the main entry point for all external clients, including the web UI, the command-line tool, and any potential third-party integrations. Its purpose is to expose pForge's capabilities through a secure, stable, and well-defined set of network endpoints, while abstracting the complexities of the internal agent-based architecture.

**Scope of Ownership**:

*   **FastAPI Application (`app.py`)**: It owns the main FastAPI application instance, which serves as the root of the web service.
*   **API Middleware (`middleware/`)**: It owns the implementation of all request-processing middleware. This includes critical cross-cutting concerns like authentication, authorization, rate-limiting, budget enforcement, and response data redaction.
*   **REST API Routes (`routes/`)**: It defines every RESTful endpoint that pForge exposes. This includes endpoints for user interaction (chat), system monitoring (metrics), file management (uploads/downloads), and inspecting proofs.
*   **Real-time Communication (`websocket/`)**: It owns the WebSocket and/or Server-Sent Events (SSE) endpoints that provide real-time, push-based communication to clients, essential for live logs and dashboard updates.
*   **Server-Side Templates (`templates/`)**: It owns any simple HTML templates used for basic, server-rendered pages like a chat client or dashboard.

**Explicitly Not in Scope**:

*   **Core Business Logic**: This directory is a presentation and routing layer. It does not contain any of the core logic for code analysis, planning, or puzzle-solving, which resides in `orchestrator/`, `agents/`, and `planner/`.
*   **Client-Side Application Code**: It does not own the React/Vite front-end application. That code resides in the `ui/` directory. The server only provides the API that the UI consumes.
*   **Database or Storage Logic**: It does not directly interact with databases or the CAS. It routes requests to backend services that handle persistence.

---

## 2. File-by-File Blueprints

### 2.1. `app.py`

*   **Responsibilities**: The main entry point for the web server, typically run with `uvicorn`.
    *   Initializes the `FastAPI` application object.
    *   Mounts all middleware from the `middleware/` directory in the correct, security-conscious order (e.g., auth before budget checks).
    *   Includes all API routers from the `routes/` directory, assigning them appropriate path prefixes.
    *   Attaches the WebSocket consumer.
    *   Defines a root `/` health-check endpoint.
*   **Tests**: An integration test will ensure the app starts up and all registered routes are available.

### 2.2. `middleware/` Subdirectory

This directory contains the pipeline of request processors.

*   **`auth.py` (Authentication)**: Checks for a `Bearer <JWT>` or `X-API-Key` header. Validates the token and attaches user/tenant information to `request.state`. If no valid token is found, it proceeds with an "anonymous" user context.
*   **`authz.py` (Authorization)**: For endpoints that require specific permissions (e.g., applying a fix), this middleware will check for a valid capability token in the request headers and verify it using `proof/capabilities.py`. It will reject requests with a 403 Forbidden error if the capability is missing or invalid.
*   **`budget_guard.py`**: Before forwarding a request to a potentially expensive operation (like a chat command that will trigger an LLM call), this middleware inspects the request for an `X-Tokens-Used-Estimate` header. It calls the `llm_clients/budget_meter.py` to verify the spend is within quota, rejecting with a 429 Too Many Requests error if not.
*   **`throttle.py`**: Provides IP-based rate limiting using a simple in-memory store (token bucket algorithm) to prevent DoS attacks.
*   **`redaction.py`**: A response middleware. Before sending a response to the client, it can optionally pass the response body through the `proof/redaction.py` scrubber to ensure no sensitive data from log messages or file snippets is accidentally leaked.

### 2.3. `routes/` Subdirectory

This directory defines the individual API endpoints.

*   **`chat.py`**:
    *   `POST /chat/nl`: The primary endpoint for natural language interaction. It accepts a JSON payload like `{"msg": "..."}`, validates it, and forwards it to the internal `chat:incoming` message bus for the `IntentRouterAgent` to process.
    *   `GET /chat/events`: A Server-Sent Events (SSE) endpoint that maintains a long-lived connection to the client. It subscribes to the `chat:outgoing` and `amp:global:events` streams and pushes formatted events to the UI for a live log feed.
*   **`metrics.py`**: Defines `GET /metrics`. This is a simple wrapper that calls the `prometheus_exporter` to generate the Prometheus text exposition format.
*   **`files.py`**:
    *   `POST /files/onboard`: An endpoint to onboard a new project. It can accept a path to a local directory (in a trusted environment) or a multipart file upload (e.g., a ZIP archive). It triggers the `sandbox.fs_manager.onboard_repo` function.
    *   `GET /files/download/{path:path}`: A secure endpoint to download a file from the current sandbox worktree. It uses the `sandbox/path_policy.py` to ensure the requested path is safe and does not escape the sandbox.
*   **`proofs.py`**: Defines `GET /proofs/{op_id}`. This allows a client to request the full, signed proof bundle associated with a specific operation ID, enabling external auditing and detailed inspection.

### 2.4. `websocket/` Subdirectory

*   **`consumer.py`**: Implements a Socket.IO or standard WebSocket endpoint (e.g., `/ws/stream`). It runs a background task that subscribes to the internal AMP bus and forwards a curated set of events (e.g., `EFF.UPDATED`, `AGENT.STATUS`, etc.) to all connected clients. This is ideal for real-time dashboard widgets that need lower latency than SSE.

### 2.5. `templates/` Subdirectory

*   **`base.html`**: A base Jinja2 template with the main HTML structure, CSS links (e.g., Tailwind CDN), and JavaScript includes (e.g., Socket.IO client).
*   **`dashboard.html`**: A simple server-rendered page that inherits from `base.html` and contains the HTML structure for the metrics dashboard, which will be populated by data from the WebSocket consumer.
*   **`chat.html`**: A simple page for the chat UI, powered by the `/chat/events` SSE stream and the `/chat/nl` POST endpoint.

---

## 3. Math & Guarantees (from README)

The `server/` directory acts as the **gatekeeper for the mathematical system**. It doesn't perform the calculations, but it guarantees that interactions with the system are orderly and secure. Its primary guarantee is **controlled access**. By enforcing authentication, authorization, and rate-limiting, it ensures that the core puzzle-solving engine cannot be easily disrupted or manipulated by unauthorized external requests.

---

## 4. Routing & Awareness

This directory is the **primary router for all external traffic**.

*   **Endpoint Routing**: FastAPI's core functionality routes incoming HTTP requests to the correct handler function in the `routes/` directory.
*   **Intent Routing**: The `routes/chat.py` endpoint is the entry point for natural language commands. It routes the user's raw text to the `IntentRouterAgent`, which then performs the more sophisticated routing to the appropriate internal agent or skill.
*   **Awareness via Middleware**: The middleware pipeline makes the server "aware" of the user's identity (`auth.py`), their permissions (`authz.py`), and their resource consumption (`budget_guard.py`), allowing it to make intelligent routing decisions (accept, reject, or throttle) for each request.

---

## 5. Token & Budget Hygiene

The `middleware/budget_guard.py` is a critical, proactive enforcement point for budget hygiene. By checking the estimated token cost of a request *before* it enters the system, it acts as a firewall that prevents the system from even beginning a task that it cannot afford to complete. This is more efficient than letting an agent start a task only to have it fail midway through due to an exhausted budget.

---

## 6. Operational Flows

*   **User Sends a Chat Message via UI**:
    1.  The user types a message in the UI and clicks "Send".
    2.  The UI's JavaScript sends a `POST` request to the `/chat/nl` endpoint.
    3.  The request passes through the middleware stack on the server.
    4.  The `routes/chat.py` handler receives the request and publishes the message to the internal `chat:incoming` message bus.
    5.  The `IntentRouterAgent` consumes the message and begins processing.
*   **Dashboard Widget Updates in Real-Time**:
    1.  The UI dashboard component establishes a WebSocket connection to `/ws/stream`.
    2.  The `websocket/consumer.py` backend task is continuously listening to the internal AMP bus.
    3.  The `EfficiencyAnalyst` publishes an `EFF.UPDATED` event.
    4.  The WebSocket consumer receives this event and immediately forwards it to all connected clients.
    5.  The UI component receives the WebSocket message and updates the efficiency gauge on the screen.

---

## 7. Testing & Backtests

*   **Testing Strategy**: The entire `server/` directory will be tested using FastAPI's `TestClient`, which allows for making simulated requests to the application without needing to run a live server.
*   **Middleware Tests**: Each middleware will be tested in isolation by creating a minimal app with the middleware and sending requests that should be passed, rejected, or modified.
*   **Route Tests**: Each endpoint in the `routes/` directory will have tests covering success cases (200 OK), client error cases (4xx, e.g., bad input), and security cases (e.g., ensuring a protected endpoint returns 403 Forbidden without a valid token).
*   **Real-time Tests**: The WebSocket and SSE endpoints will be tested to ensure they establish connections correctly and stream data as expected when mock events are published to the backend bus.

---

## 8. Security & Policy

This directory is the **primary security boundary** against all external network-based threats.

| Security Concern | Implemented By |
| :--- | :--- |
| Unauthorized Access | `middleware/auth.py`, `middleware/authz.py` |
| Denial of Service | `middleware/throttle.py` |
| Resource Exhaustion | `middleware/budget_guard.py` |
| Data Exfiltration | `middleware/redaction.py` (on responses) |
| Insecure File Access | `routes/files.py` (using `sandbox/path_policy.py`) |

It is the implementation layer for all access control and network security policies.

---

## 9. Readme Cross-Reference

The `server/` directory provides the "conversation interface" and the "user controls" for the puzzle-solving system described in the `README.md`.

| Server Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `routes/chat.py`, `websocket/` | The implementation of the "conversation interface" where the user can collaborate with the agents, observe their progress, and provide input. |
| API Endpoints (`/metrics`, `/files`) | The control panel for the puzzle-solving machine, allowing the user to check its status, give it a new puzzle to solve, and inspect the results. |
| Middleware | The set of safety rules and physical limits of the room where the puzzle is being solved. It ensures that only authorized people can enter, that they don't break the table, and that they can't run off with the puzzle pieces. |

This directory makes the powerful backend of pForge accessible and usable by humans and other computer systems.
