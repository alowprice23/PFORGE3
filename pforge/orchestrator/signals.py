from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

class MsgType(str, Enum):
    OBS_TICK = "obs.tick"
    TESTS_FAILED = "tests.failed"
    TESTS_PASSED = "tests.passed"
    FIX_TASK = "task.fix"
    FIX_PATCH_APPLIED = "patch.applied"
    FIX_PATCH_REJECTED = "patch.rejected"
    PREDICTIONS_MADE = "predictions.made"
    MISFIT_DETECTED = "misfit.detected"
    FALSE_PIECE_DETECTED = "false_piece.detected"

@dataclass
class Message:
    """A standardized message object for the in-memory bus."""
    type: MsgType
    payload: Dict[str, Any]

# From proof/PLAN.md, this is needed by proof/bundle.py
@dataclass
class ProofObligation:
    id: str
    ok: Optional[bool] = None
    witness: Optional[Dict[str, Any]] = None

# From orchestrator/PLAN.md, these are the delta signals for the efficiency engine
@dataclass
class BaseDelta:
    agent_name: str
    value: float

@dataclass
class GapDelta(BaseDelta):
    """Represents a change in the number of gaps (E)."""
    pass

@dataclass
class MisfitDelta(BaseDelta):
    """Represents a change in the number of misfits (M)."""
    pass

@dataclass
class FalsePieceDelta(BaseDelta):
    """Represents a change in the number of false pieces (F)."""
    pass

@dataclass
class RiskDelta(BaseDelta):
    """Represents a change in the risk (R)."""
    pass

@dataclass
class BacktrackDelta(BaseDelta):
    """Represents a change in the number of backtracks (B)."""
    pass

@dataclass
class EntropyDelta(BaseDelta):
    """Represents a change in the entropy (H)."""
    pass

@dataclass
class PhiDelta(BaseDelta):
    """Represents a change in the number of removed false pieces (φ)."""
    pass

# From orchestrator/PLAN.md, QED and RECOVERY signals
@dataclass
class QEDSignal:
    """Signal that the puzzle is considered solved."""
    proof_bundle_id: str

@dataclass
class RecoverySignal:
    """Signal that a recovery action has been taken."""
    action: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
