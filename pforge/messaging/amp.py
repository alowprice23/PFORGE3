from __future__ import annotations
import time
import uuid
from typing import Dict, Any, Optional, Union

from pydantic import BaseModel, Field

class AMPMessage(BaseModel):
    """
    The Agent Message Protocol (AMP) schema.
    """
    op_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()))

    type: str = Field(...)
    actor: str = Field(...)

    causality: Dict[str, Optional[str]] = Field(default_factory=dict)
    snap_sha: str = Field(...)

    payload: Dict[str, Any] = Field(default_factory=dict)
    proof: Optional["ProofBundle"] = Field(None)
    sig: Optional[str] = Field(None)

    def to_json(self) -> str:
        """Serializes the message to a compact JSON string."""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw_json: Union[str, bytes]) -> AMPMessage:
        """Deserializes a JSON string into an AMPMessage object."""
        return cls.model_validate_json(raw_json)
