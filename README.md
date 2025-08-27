# pForge

pForge is an experimental, agent-based system designed to automatically diagnose and repair issues in software projects. It uses a swarm of specialized AI agents that collaborate locally to find bugs, plan fixes, and verify their work.

## Core Concept: Test-Driven Repair

The core workflow of pForge is a local, test-driven repair cycle:

1.  **Observe**: An `ObserverAgent` runs the project's test suite to detect failures.
2.  **Plan**: A `PlannerAgent` receives the details of the failed test and formulates a specific, actionable plan to fix the underlying bug.
3.  **Fix**: A `FixerAgent` receives the plan, uses an LLM to generate a code patch, and applies it to the source file in a sandboxed environment.
4.  **Verify**: The `FixerAgent` immediately re-runs the failing test to verify that the patch was successful.

This creates a tight, "self-healing" feedback loop where the system's actions are directly guided by empirical evidence from the test suite. All communication between agents happens in-memory, with no server or network dependencies.

## Getting Started

pForge is a command-line tool. The main command for launching the repair workflow is:

```bash
pforge doctor run /path/to/your/project
```

This will trigger the local agent swarm to begin observing and repairing the specified project.

---

*This project is under active development. The architecture and capabilities are subject to change.*
