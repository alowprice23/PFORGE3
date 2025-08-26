"""
The Storage package provides the durable, verifiable, and transactionally-safe
persistence layers for all of pForge's critical state.

It is the system's long-term memory, responsible for ensuring that data,
once written, is preserved with integrity and can be retrieved efficiently.

Modules:
- cas: The Content-Addressable Store for immutable file content.
- sqlite: Contains the canonical SQL schemas for SQLite databases.
- fslock: A cross-platform file locking utility for safe concurrent access.
"""

from .cas import read_blob, write_blob, DataCorruptionError
from .fslock import FileLock, FileLockException

__all__ = [
    "read_blob",
    "write_blob",
    "DataCorruptionError",
    "FileLock",
    "FileLockException",
]
