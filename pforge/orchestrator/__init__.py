"""
The Orchestrator package is the heart of the pForge system.

It is responsible for the main control loop, managing the lifecycle of agents,
and calculating the system's overall efficiency based on the mathematical
puzzle-solving framework.

Modules:
- core: The main application entry point and agent lifecycle manager.
- agent_registry: Discovers and registers available agent classes.
- state_bus: Manages the global `PuzzleState` via an in-memory bus.
- signals: Defines the data contracts for events.
"""

from .core import Orchestrator
from .agent_registry import AgentRegistry
from .state_bus import StateBus, PuzzleState
from .efficiency_engine import EfficiencyEngine
from . import signals

__all__ = [
    "Orchestrator",
    "AgentRegistry",
    "StateBus",
    "PuzzleState",
    "EfficiencyEngine",
    "signals",
]
