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
from .observer import ObserverAgent
from .planner_agent import PlannerAgent
from .fixer_agent import FixerAgent
from .backtracker_agent import BacktrackerAgent
from .predictor_agent import PredictorAgent
from .misfit_agent import MisfitAgent
from .false_piece_agent import FalsePieceAgent
from .summarizer_agent import SummarizerAgent

# A dictionary to make all agent classes easily accessible for registration.
AGENT_CLASSES = {
    "observer": ObserverAgent,
    "planner": PlannerAgent,
    "fixer": FixerAgent,
    "backtracker": BacktrackerAgent,
    "predictor": PredictorAgent,
    "misfit": MisfitAgent,
    "false_piece": FalsePieceAgent,
    "summarizer": SummarizerAgent,
}

__all__ = [
    "BaseAgent",
    "ObserverAgent",
    "PlannerAgent",
    "FixerAgent",
    "BacktrackerAgent",
    "PredictorAgent",
    "MisfitAgent",
    "FalsePieceAgent",
    "SummarizerAgent",
    "AGENT_CLASSES",
]
