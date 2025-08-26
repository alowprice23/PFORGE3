"""
The Agents package contains the concrete implementations of all specialized,
autonomous agents that constitute the pForge system.

Each agent is a distinct, modular service responsible for executing a
specific part of the overall puzzle-solving workflow.

Modules:
- base_agent: The abstract base class for all agents.
- observer_agent: The primary sensor, building the evidence graph.
- spec_oracle_agent: The arbiter of correctness, evaluating specification
  constraints (Φ).
- ... and many more agents for planning, fixing, etc.
"""

from .base_agent import BaseAgent
from .observer_agent import ObserverAgent
from .spec_oracle_agent import SpecOracleAgent

# A dictionary to make all agent classes easily accessible for registration.
AGENT_CLASSES = {
    "observer": ObserverAgent,
    "spec_oracle": SpecOracleAgent,
    # Other agents will be added here as they are implemented.
}

__all__ = [
    "BaseAgent",
    "ObserverAgent",
    "SpecOracleAgent",
    "AGENT_CLASSES",
]
