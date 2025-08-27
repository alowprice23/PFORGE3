from __future__ import annotations
import orjson
import time
import uuid
from typing import Dict, Any, Optional, Union

from pydantic import BaseModel, Field

# To avoid circular dependency issues at runtime, we can use a string forward reference
# for ProofBundle if needed, but for now, a type hint will suffice.
from pforge.proof.bundle import ProofBundle

class AMPMessage(BaseModel):
    """
    The Agent Message Protocol (AMP) schema.

    This is the canonical data structure for all events passed between agents
    on the message bus. It is designed to be auditable, idempotent, and
    verifiable.
    """
    op_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The producer's idempotency key.")
    at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()), description="ISO 8601 timestamp of event creation.")

    type: str = Field(..., description="The event type, e.g., 'FIX.PATCH_APPLIED'.")
    actor: str = Field(..., description="The name of the agent or system component that produced the event.")

    causality: Dict[str, Optional[str]] = Field(default_factory=dict, description="Causality tracking, e.g., {'prev': 'op_id_123', 'thread': 'solve_cycle_42'}.")
    snap_sha: str = Field(..., description="The content hash of the Σ snapshot this event pertains to.")

    payload: Dict[str, Any] = Field(default_factory=dict, description="The main data payload of the event.")
    proof: Optional[ProofBundle] = Field(None, description="An optional, verifiable proof bundle associated with the event's claims.")
    sig: Optional[str] = Field(None, description="A cryptographic signature of the event content.")

    def to_json(self) -> str:
        """Serializes the message to a compact JSON string."""
        # The `exclude_none=True` is important to keep payloads clean.
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw_json: Union[str, bytes]) -> AMPMessage:
        """Deserializes a JSON string into an AMPMessage object."""
        return cls.model_validate_json(raw_json)
