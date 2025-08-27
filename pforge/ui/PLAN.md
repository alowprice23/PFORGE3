# PLAN: `ui/` Directory

## 1. Directory Purpose & Scope

**Purpose**: The `ui/` directory contains the source code for the React-based web user interface for pForge. It provides a rich, interactive experience for users to monitor the system's progress, interact with the conversational agent, and inspect the proofs and artifacts that the system generates. This directory is what makes the complex inner workings of pForge accessible and understandable to a human user.

**Scope of Ownership**:

*   **React Application**: It owns the entire React application, built with Vite and TypeScript.
*   **API Client (`api/client.ts`)**: It owns the client-side code for interacting with the FastAPI backend, including fetching metrics, proofs, and other data.
*   **UI Components (`components/`)**: It owns the implementation of all the React components that make up the UI, such as the chat window, the metrics panel, and the proof viewer.
*   **Styling**: It owns the styling for the application, which is implemented using Tailwind CSS.

**Explicitly Not in Scope**:

*   **Backend Logic**: This directory contains only frontend code. All the backend logic resides in the `server/` and other directories.
*   **HTML Templates**: The base HTML templates are served by the `server/` directory. This directory contains the JavaScript and CSS that is loaded into those templates.

---

## 2. File-by-File Blueprints

**Status Key:**
*   `[ ]` - Not Started
*   `[~]` - In Progress
*   `[x]` - Completed

### 2.1. `public/favicon.ico` [x]

*   **Responsibilities**: To provide the favicon for the web application.

### 2.2. `src/index.tsx` [x]

*   **Responsibilities**: To be the main entry point for the React application. It renders the `App` component into the DOM.

### 2.3. `src/App.tsx` [x]

*   **Responsibilities**: To define the main layout and routing for the application. It uses `react-router-dom` to define the routes for the different pages of the application (chat, dashboard, etc.).

### 2.4. `src/api/client.ts` [ ]

*   **Responsibilities**: To provide a typed, high-level client for the FastAPI backend.
    *   It uses `axios` or a similar library to make HTTP requests to the backend.
    *   It provides functions for fetching metrics, proofs, and other data.
*   **Interfaces**: Used by the React components to fetch data from the backend.

### 2.5. `src/components/` Subdirectory

This directory contains the individual React components that make up the UI.

*   **`ChatWindow.tsx` [ ]**: Implements the main chat interface, with support for user input and real-time updates from the conversational agent.
*   **`MetricsPanel.tsx` [ ]**: Displays the live metrics from the system, such as the efficiency score `E` and the entropy `H`.
*   **`PlannerPanel.tsx` [ ]**: Displays the current plan from the `PlannerAgent`, including the chosen actions and their priorities.
*   **`ProofViewer.tsx` [ ]**: A modal component that can display a formatted view of a proof bundle.
*   **`DiffCard.tsx` [ ]**: A component for displaying unified diffs with syntax highlighting.
*   **`ConstellationGraph.tsx` [ ]**: A component for visualizing the constellation memory of the agentic CLI.
*   **`AgentLog.tsx` [ ]**: A component for displaying the real-time log of agent activity.

### 2.6. `src/utils/llmColors.ts` [x]

*   **Responsibilities**: To provide a mapping from agent names to theme colors, for use in the UI.

---

## 3. Math & Guarantees (from README)

The `ui/` directory is the primary way for a human user to observe and interact with the mathematical state of the pForge system. The `MetricsPanel` and `PlannerPanel` provide a real-time view of the `E`, `H`, and `P` values that drive the system. The `ProofViewer` makes the mathematical guarantees of the system transparent and auditable. The `ConstellationGraph` provides a visual representation of the learning process of the agentic CLI.

This directory is what makes the system's claim to be "human-in-the-loop" a reality.
