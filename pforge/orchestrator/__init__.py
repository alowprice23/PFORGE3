"""
The Orchestrator package is the heart of the pForge system.

It is responsible for the main control loop, managing the lifecycle of agents,
and calculating the system's overall efficiency based on the mathematical
puzzle-solving framework.

Modules:
- core: The main application entry point and tick loop.
- agent_registry: Discovers and manages available agent classes.
- scheduler: The (future) adaptive economy for spawning and retiring agents.
- state_bus: Manages the global `PuzzleState` via Redis.
- efficiency_engine: Implements the core `E_intelligent` formula.
- signals: Defines the data contracts for events and metric deltas.
"""

from .core import Orchestrator, load_config
from .agent_registry import AgentRegistry
from .state_bus import StateBus, PuzzleState
from .efficiency_engine import EfficiencyEngine
from . import signals

__all__ = [
    "Orchestrator",
    "load_config",
    "AgentRegistry",
    "StateBus",
    "PuzzleState",
    "EfficiencyEngine",
    "signals",
]
