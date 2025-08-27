"""
The Messaging package provides the schema and transport abstraction for all
inter-agent communication in the pForge system.
"""

from .amp import AMPMessage
from .in_memory_bus import InMemoryBus
from pforge.proof.bundle import ProofBundle

AMPMessage.model_rebuild()

__all__ = [
    "AMPMessage",
    "InMemoryBus",
]
