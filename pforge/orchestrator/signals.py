from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Dict, Any, Optional
from enum import Enum

class MsgType(str, Enum):
    OBS_TICK = "OBS.TICK"
    PLAN_PROPOSED = "PLAN.PROPOSED"
    FIX_PATCH_PROPOSED = "FIX.PATCH_PROPOSED"
    FIX_PATCH_APPLIED = "FIX.PATCH_APPLIED"
    FIX_PATCH_REJECTED = "FIX.PATCH_REJECTED"
    SPEC_CHECKED = "SPEC.CHECKED"
    CONFLICT_FOUND = "CONFLICT.FOUND"
    CONFLICT_RESOLVED = "CONFLICT.RESOLVED"
    BACKTRACK_REQUEST = "BACKTRACK.REQUEST"
    BACKTRACK_COMPLETED = "BACKTRACK.COMPLETED"
    EFF_UPDATED = "EFF.UPDATED"
    INTENT_ROUTED = "INTENT.ROUTED"
    QED_EMITTED = "QED.EMITTED"
    RECOVERY_ACTION = "RECOVERY.ACTION"

@dataclass
class BaseDelta:
    agent: str
    value: int | float
    ts: float

@dataclass
class GapDelta(BaseDelta):
    kind: Literal["gap"] = "gap"

@dataclass
class MisfitDelta(BaseDelta):
    kind: Literal["misfit"] = "misfit"

@dataclass
class FalsePieceDelta(BaseDelta):
    kind: Literal["false_piece"] = "false_piece"

@dataclass
class RiskDelta(BaseDelta):
    kind: Literal["risk"] = "risk"

@dataclass
class BacktrackDelta(BaseDelta):
    kind: Literal["backtrack"] = "backtrack"

@dataclass
class EntropyDelta(BaseDelta):
    kind: Literal["entropy"] = "entropy"

@dataclass
class Message:
    """A standardized message object for the in-memory bus."""
    type: MsgType
    payload: Dict[str, Any]

@dataclass
class ProofObligation:
    id: str
    ok: Optional[bool] = None
    witness: Optional[Dict[str, Any]] = None
