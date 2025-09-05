# pForge API Reference

This document provides a reference for the public API of the pForge system. The API allows for interaction with the agentic system, monitoring its status, and retrieving data and proofs.

The base URL for all endpoints is the address of the running pForge server.

## 1. Chat API

The Chat API provides endpoints for interacting with the pForge system using natural language.

### `POST /api/chat/nl`

*   **Summary**: Submit a natural language message to the pForge system.
*   **Description**: This endpoint accepts a natural language message from a user, which is then processed by the `IntentRouterAgent` to be converted into a structured command for the pForge system.
*   **Request Body**:
    *   `Content-Type`: `application/json`
    *   **Payload**:
        ```json
        {
          "msg": "Your natural language message here"
        }
        ```
*   **Responses**:
    *   `200 OK`: The message was successfully queued for processing.
        ```json
        {
          "status": "message_queued",
          "user": "anonymous",
          "reply": "This is a placeholder response."
        }
        ```
    *   `400 Bad Request`: The `msg` field was empty.

### `GET /api/chat/events`

*   **Summary**: Subscribe to a real-time stream of server events.
*   **Description**: This is a Server-Sent Events (SSE) endpoint that allows clients to receive a continuous stream of events from the pForge system, such as agent actions, state changes, and log messages.
*   **Responses**:
    *   `200 OK`: A streaming response with `Content-Type: text/event-stream`. Events are formatted as:
        ```
        event: message
        data: {"message": "placeholder event"}

        ```

## 2. Monitoring API

The Monitoring API provides endpoints for checking the health and performance of the pForge system.

### `GET /api/healthz`

*   **Summary**: A simple health check endpoint.
*   **Description**: Returns a status of "ok" if the server is running and responsive.
*   **Responses**:
    *   `200 OK`:
        ```json
        {
          "status": "ok"
        }
        ```

### `GET /metrics`

*   **Summary**: Expose Prometheus metrics.
*   **Description**: Provides system metrics in the Prometheus text-based format, suitable for scraping by a Prometheus server.
*   **Responses**:
    *   `200 OK`: A text response with `Content-Type: text/plain; version=0.0.4; charset=utf-8` containing the Prometheus metrics.

## 3. Files API

The Files API provides endpoints for managing files within the pForge sandbox.

### `POST /api/files/onboard`

*   **Summary**: Onboard a new project from a ZIP archive.
*   **Description**: Accepts a ZIP file, extracts it, and onboards it into the pForge sandbox system, creating an initial commit in the Content-Addressable Store (CAS).
*   **Request Body**:
    *   `Content-Type`: `multipart/form-data`
    *   **File**: A ZIP archive of the project.
*   **Responses**:
    *   `200 OK`: The project was successfully onboarded.
        ```json
        {
          "status": "onboarding_successful",
          "initial_commit_sha": "..."
        }
        ```
    *   `400 Bad Request`: The uploaded file was not a ZIP archive.
    *   `500 Internal Server Error`: An error occurred during the onboarding process.

### `GET /api/files/download/{file_path:path}`

*   **Summary**: Download a file from the sandbox.
*   **Description**: Provides secure, read-only access to files within the current sandbox worktree. It includes protection against path traversal attacks.
*   **Path Parameters**:
    *   `file_path`: The full path to the file within the sandbox.
*   **Responses**:
    *   `200 OK`: The requested file.
    *   `403 Forbidden`: Access to the requested path is not allowed.
    *   `404 Not Found`: The requested file does not exist.

## 4. Proofs API

The Proofs API provides endpoints for retrieving the verifiable evidence of the system's actions.

### `GET /api/proofs/{op_id}`

*   **Summary**: Retrieve a proof bundle by operation ID.
*   **Description**: Fetches the full, signed proof bundle associated with a specific operation ID (`op_id`). This allows for external auditing and verification of the system's claims.
*   **Path Parameters**:
    *   `op_id`: The unique identifier for the operation.
*   **Responses**:
    *   `200 OK`: The full, signed AMP message containing the proof bundle.
    *   `404 Not Found`: No proof bundle was found for the given `op_id`.
