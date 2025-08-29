# PLAN: `server/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `server/` directory contains the FastAPI web application that serves as the primary API and user interface for pForge. It exposes the system's capabilities through a set of RESTful endpoints, a WebSocket for real-time events, and a simple web UI for chat and monitoring. This directory is the main entry point for all external interactions with the pForge system.

**Scope of Ownership**:

*   **FastAPI Application (`app.py`)**: It owns the main FastAPI application instance, including the mounting of all middleware and routers.
*   **Middleware (`middleware/`)**: It owns the implementation of all the custom middleware used by the application, including authentication, authorization, token budgeting, rate limiting, and data redaction.
*   **API Routes (`routes/`)**: It owns the implementation of all the API endpoints, which provide access to the system's chat, metrics, file, and proof-related functionalities.
*   **WebSocket Consumer (`websocket/`)**: It owns the Socket.IO consumer that bridges the AMP bus to the web UI, providing real-time updates on agent activity and system state.
*   **HTML Templates (`templates/`)**: It owns the Jinja2 templates for the simple web UI, including the base layout, the dashboard, and the chat interface.

**Explicitly Not in Scope**:

*   **Core Logic**: This directory is a thin presentation layer and does not contain any of the core business logic of the pForge system. It calls the services provided by the other directories to perform its work.
*   **Frontend Application**: While it serves the HTML templates, the `server/` directory does not own the implementation of the React frontend application. That resides in the `ui/` directory.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `app.py` [x]

*   **Responsibilities**: To be the main entry point for the FastAPI application.
    *   It initializes the FastAPI app.
    *   It mounts all the middleware and routers.
    *   It includes the WebSocket bridge for real-time events.
*   **Interfaces**: This is the main entry point for the `uvicorn` server.

### 2.2. `middleware/` Subdirectory

*   **`auth.py` [ ]**: Implements authentication using JWT or API keys.
*   **`authz.py` [ ]**: Implements authorization using capability tokens.
*   **`budget_guard.py` [ ]**: Enforces the token budget for each tenant.
*   **`throttle.py` [ ]**: Implements rate limiting for shell commands and other expensive operations.
*   **`redaction.py` [ ]**: Scrubs sensitive information from all outgoing payloads.

### 2.3. `routes/` Subdirectory

*   **`chat.py` [ ]**: Implements the `/chat` endpoints for both the conversational CLI and the web UI.
*   **`metrics.py` [ ]**: Exposes the `/metrics` endpoint for Prometheus.
*   **`files.py` [ ]**: Provides endpoints for downloading files from the sandbox and for viewing diffs.
*   **`proofs.py` [ ]**: Provides an endpoint for retrieving and verifying proof bundles by their ID.

### 2.4. `websocket/consumer.py` [ ]

*   **Responsibilities**: To bridge the Redis AMP bus to the Socket.IO WebSocket.
    *   It consumes events from the `amp:global:events` stream.
    *   It broadcasts these events to all connected WebSocket clients.
*   **Interfaces**: Used by the React frontend to receive real-time updates.

### 2.5. `templates/` Subdirectory

*   **`base.html` [ ]**: The base Jinja2 template with the common layout and styles.
*   **`dashboard.html` [ ]**: The template for the metrics dashboard.
*   **`chat.html` [ ]**: The template for the conversational chat UI.

---

## 3. Math & Guarantees (from README)

The `server/` directory is the primary interface for observing the mathematical state of the system. The `/metrics` endpoint exposes the `E` and `H` values, and the WebSocket pushes real-time updates on the system's progress. The `/proofs` endpoint allows for the verification of the mathematical guarantees of the system.
