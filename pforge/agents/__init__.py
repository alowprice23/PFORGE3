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
from .planner_agent import PlannerAgent
from .fixer_agent import FixerAgent
from .predictor_agent import PredictorAgent
from .misfit_agent import MisfitAgent
from .false_piece_agent import FalsePieceAgent
from .backtracker_agent import BacktrackerAgent
from .summarizer_agent import SummarizerAgent

# A dictionary to make all agent classes easily accessible for registration.
AGENT_CLASSES = {
    "observer": ObserverAgent,
    "spec_oracle": SpecOracleAgent,
    "planner": PlannerAgent,
    "fixer": FixerAgent,
    "predictor": PredictorAgent,
    "misfit": MisfitAgent,
    "false_piece": FalsePieceAgent,
    "backtracker": BacktrackerAgent,
    "summarizer": SummarizerAgent,
}

__all__ = [
    "BaseAgent",
    "ObserverAgent",
    "SpecOracleAgent",
    "PlannerAgent",
    "FixerAgent",
    "PredictorAgent",
    "MisfitAgent",
    "FalsePieceAgent",
    "BacktrackerAgent",
    "SummarizerAgent",
    "AGENT_CLASSES",
]
