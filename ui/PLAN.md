# PLAN: `ui/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `ui/` directory provides a rich, interactive, and intuitive graphical user interface (GUI) for the pForge system. It serves as the primary visual entry point for users, translating the complex, event-driven backend operations into a human-understandable format. Its purpose is to make pForge accessible, transparent, and easy to monitor, enabling users to chat with the system, visualize its progress, and inspect its results in detail.

**Scope of Ownership**:

*   **Client-Side Application**: It owns the entire React/Vite single-page application (SPA).
*   **Component Library (`components/`)**: It owns all React components that make up the user interface, from high-level panels like the `ChatWindow` and `MetricsPanel` to granular components like `DiffCard` and `ProofViewer`.
*   **API Client Logic (`api/client.ts`)**: It owns the dedicated client-side module responsible for all communication with the backend server. This includes making REST API calls and managing the real-time WebSocket/SSE connections.
*   **State Management**: It is responsible for managing all client-side state, such as the chat history, the current metrics snapshot, and UI-specific state (e.g., which modal is open).
*   **Static Assets (`public/`)**: It owns all static assets that are served directly to the browser, such as the favicon.

**Explicitly Not in Scope**:

*   **Backend Logic**: The `ui/` directory is a "thin client." It contains no core application logic. All business logic, from agent orchestration to proof verification, resides on the server. The UI is a consumer of the server's API.
*   **Server-Side Rendering**: While it may be served by the FastAPI server in production, it is a client-side rendered application. The `server/templates/` directory is separate and used for simpler, server-rendered pages.
*   **Design System**: This plan assumes the use of a standard CSS framework or component library (e.g., Tailwind CSS, Material-UI) but does not own the library itself.

---

## 2. File-by-File Blueprints

### 2.1. `public/` Subdirectory

*   **`favicon.ico`**: The application icon displayed in the browser tab. A simple, static asset.

### 2.2. `src/` Subdirectory

This contains the main source code for the React application.

*   **`index.tsx`**: The main entry point. It uses `ReactDOM.createRoot` to render the root `App` component into the `index.html` file's root div. It also sets up the top-level providers, such as the `BrowserRouter` for routing.
*   **`App.tsx`**: The top-level application component.
    *   **Responsibilities**: Defines the overall page layout, including a persistent header with navigation links. It uses `react-router-dom` to define the routes for the main application views (`/`, `/dash`, `/logs`, etc.) and renders the appropriate component for the current URL.
*   **`api/client.ts`**:
    *   **Responsibilities**: To centralize all communication with the backend.
    *   **REST API**: Exports functions that wrap `axios` or `fetch` for each API endpoint (e.g., `sendMessage(msg: string)`, `getProof(opId: string)`). It will handle setting the `Authorization` header for all requests.
    *   **Real-time**: Exports a singleton instance of the Socket.IO client, configured to connect to the server's `/ws/stream` endpoint. This allows components to subscribe to and unsubscribe from real-time events.
*   **`components/` Subdirectory**:
    *   **`ChatWindow.tsx`**: The primary interactive component. It will manage an array of chat messages in its state. It will render a scrollable log of messages and a text input form. On form submission, it will call the `api/client.ts` to send the message and will listen to the real-time event streams to display new log entries and assistant replies.
    *   **`MetricsPanel.tsx`**: A dashboard component. It will subscribe to the `metrics.tick` event from the WebSocket stream. On receiving a new metrics snapshot, it will update its state and re-render the gauges for Efficiency (E), Entropy (H), Gaps, Misfits, etc.
    *   **`PlannerPanel.tsx`**: Visualizes the `PlannerAgent`'s state. It listens for `PLAN.PROPOSED` events and displays the chosen actions, their priorities, and the current budget utilization. It could use color-coding to indicate high-priority or high-risk items.
    *   **`ProofViewer.tsx`**: A detailed view, likely implemented as a modal dialog. It takes a `ProofBundle` object as a prop and renders its contents in a structured and readable way, using sub-components like `DiffCard` to display details.
    *   **`DiffCard.tsx`**: A specialized component that takes a unified diff string as a prop and renders it with syntax highlighting and clear `+` (green) and `-` (red) indicators for each line.
    *   **`ConstellationGraph.tsx`**: An advanced data visualization component. It will fetch the constellation data from a dedicated API endpoint and use a library like D3.js, Vis.js, or React Flow to render the learned routes as an interactive graph. Nodes will represent skills, and edges will be weighted/colored by their learned reward.
    *   **`AgentLog.tsx`**: A simple, real-time log viewer that subscribes to the `amp:global:events` stream and displays a raw, color-coded feed of all agent actions, useful for detailed debugging.
*   **`utils/llmColors.ts`**: A simple utility function that takes an agent name string and returns a consistent hex color code. This ensures that agents are represented by the same color across all UI components (`AgentLog`, graphs, etc.), improving readability.

---

## 3. Math & Guarantees (from README)

The `ui/` directory's primary role is to provide a **guarantee of transparency** for the mathematical framework. It makes the abstract numbers and states concrete and visible.

*   **Visualizing E and H**: The `MetricsPanel.tsx` directly renders the values of the core Efficiency and Entropy formulas, allowing a user to intuitively grasp the health of the system at a glance.
*   **Visualizing P**: The `PlannerPanel.tsx` shows the output of the Priority formula `P`, making it clear *why* the system is choosing to work on a specific task.
*   **Visualizing Proofs**: The `ProofViewer.tsx` makes the concept of a "proof" tangible. Instead of an abstract guarantee, the user can see the hashed test reports, the constraint check results, and the exact diff that was applied.

This visualization turns the mathematical guarantees of the backend into something a human can see and trust.

---

## 4. Routing & Awareness

*   **Client-Side Routing**: `App.tsx` uses `react-router-dom` to handle navigation between the different views of the application without requiring a full page reload.
*   **Backend Awareness**: The UI's awareness of the backend state is managed entirely by the `api/client.ts`. It subscribes to the real-time event streams, receives updates, and uses a client-side state management solution (e.g., React Context, Zustand, or Redux) to propagate those updates to the relevant components, which then re-render.

---

## 5. Token & Budget Hygiene

The UI contributes to budget hygiene by making costs visible. The `MetricsPanel.tsx` or a dedicated budget component can display the data from the `pforge_tokens_used` Prometheus metric, showing the user the real-time cost of their interactions and the total budget remaining. This transparency encourages more mindful use of expensive LLM-driven features.

---

## 6. Operational Flows

*   **User Interacts with the Chat**:
    1.  User types "fix the auth bug" into the `ChatWindow.tsx` input field and presses Enter.
    2.  The component's `onSubmit` handler calls `api/client.ts.sendMessage("fix the auth bug")`.
    3.  The client makes a `POST` request to the `/chat/nl` endpoint.
    4.  Simultaneously, the `ChatWindow` is listening to the WebSocket stream. As the backend agents start working on the request, `AGENT.LOG` and other AMP events are streamed to the UI and displayed in the log panel.
    5.  When the backend process is complete, the `SummarizerAgent`'s final reply is sent over the stream and displayed as a message from the "pForge" assistant.

---

## 7. Testing & Backtests

*   **Component Unit Tests**: Each component in the `components/` directory will be tested in isolation using React Testing Library. The tests will provide mock props and assert that the component renders correctly and that user interactions (like clicks) trigger the correct callbacks.
*   **API Client Mocking**: The tests will use a library like Mock Service Worker (`msw`) to intercept all API calls made by `api/client.ts`. This allows for testing component behavior with a variety of simulated backend responses (success, error, loading states) without needing a live backend server.
*   **End-to-End (E2E) Tests**: A small suite of E2E tests using a framework like Cypress or Playwright will test critical user flows on a live (or fully mocked) version of the application. For example, an E2E test would simulate a user logging in, sending a chat message, and verifying that a response appears on the screen.

---

## 8. Security & Policy

*   **XSS Prevention**: By using React for rendering, the UI is protected against most common Cross-Site Scripting (XSS) vulnerabilities. The plan must specify that any use of `dangerouslySetInnerHTML` is forbidden unless it is paired with a robust HTML sanitization library.
*   **Authentication Token Handling**: The `api/client.ts` is responsible for securely handling the user's authentication token (JWT). It should be stored in a secure manner (e.g., a secure, HTTP-only cookie is preferred over `localStorage`) and attached to all outgoing API requests.

---

## 9. Readme Cross-Reference

The `ui/` directory provides the visual "conversation interface" and "dashboard" for the puzzle-solving system from the `README.md`.

| UI Component | README.md Concept Cross-Reference |
| :--- | :--- |
| `ChatWindow.tsx` | The direct, interactive "conversation" with the intelligent solver, where the user can collaborate and guide the process. |
| `MetricsPanel.tsx` | The "scoreboard" that shows the puzzle's state: the efficiency `E` (how close you are to finished), the entropy `H` (how messy the board is), and the number of `gaps`. |
| `ProofViewer.tsx` | The "magnifying glass" that allows the user to inspect any piece or connection on the board to verify that it is indeed a perfect fit. |
| `ConstellationGraph.tsx` | A visual map of the solver's "brain," showing the strategies and paths it has learned are most effective for this type of puzzle. |

This directory makes the abstract power of the pForge system visible, understandable, and trustworthy to a human user.
