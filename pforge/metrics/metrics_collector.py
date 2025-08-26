from __future__ import annotations
from prometheus_client import Gauge, Counter, Histogram
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pforge.orchestrator.state_bus import PuzzleState

# --- Core Efficiency and State Metrics ---
PFORGE_EFFICIENCY = Gauge(
    "pforge_efficiency",
    "The global puzzle efficiency score (E)."
)
PFORGE_ENTROPY = Gauge(
    "pforge_entropy",
    "The global system entropy score (H)."
)
PFORGE_GAPS = Gauge(
    "pforge_gaps_total",
    "The current number of open gaps or issues (E)."
)
PFORGE_MISFITS = Gauge(
    "pforge_misfits_total",
    "The current number of misfits (M)."
)
PFORGE_FALSE_PIECES = Gauge(
    "pforge_false_pieces_total",
    "The current number of identified false pieces (F)."
)

# --- Agent and Orchestrator Metrics ---
PFORGE_AGENTS_ACTIVE = Gauge(
    "pforge_agents_active_total",
    "The number of currently active agents.",
    ["agent_type"]
)
PFORGE_ORCHESTRATOR_TICK_DURATION = Histogram(
    "pforge_orchestrator_tick_duration_seconds",
    "The duration of the main orchestrator tick loop."
)

# --- Resource and Budget Metrics ---
PFORGE_TOKENS_USED_TOTAL = Counter(
    "pforge_tokens_used_total",
    "The total number of LLM tokens used.",
    ["vendor", "model"]
)
PFORGE_BUDGET_USAGE_PERCENT = Gauge(
    "pforge_budget_usage_percent",
    "The percentage of the token budget that has been consumed.",
    ["tenant"]
)

# --- Action and Outcome Metrics ---
PFORGE_PATCHES_APPLIED_TOTAL = Counter(
    "pforge_patches_applied_total",
    "The total number of patches successfully applied."
)
PFORGE_ROLLBACKS_TOTAL = Counter(
    "pforge_rollbacks_total",
    "The total number of rollbacks initiated due to failures or conflicts."
)
PFORGE_RECOVERY_ACTIONS_TOTAL = Counter(
    "pforge_recovery_actions_total",
    "The total number of environmental recovery actions taken.",
    ["action_type"]
)


def update_state_gauges(state: PuzzleState):
    """
    A helper function to update all state-related gauges at once.
    This is typically called by the EfficiencyAnalyst agent after it has
    aggregated all the latest deltas.
    """
    PFORGE_EFFICIENCY.set(state.efficiency)
    PFORGE_ENTROPY.set(state.entropy)
    PFORGE_GAPS.set(state.gaps)
    PFORGE_MISFITS.set(state.misfits)
    PFORGE_FALSE_PIECES.set(state.false_pieces)
