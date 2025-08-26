"""
The Sandbox package provides a safe, isolated, and stateful filesystem
environment where agents can analyze and modify code.

It is the tangible implementation of the "puzzle board" where all work is
performed, abstracting away the complexities of file management and versioning.

Modules:
- fs_manager: High-level functions for managing the sandbox lifecycle
  (onboarding, snapshots, checkouts, rollbacks).
- diff_utils: Generates structured and human-readable differences between
  any two sandbox snapshots.
- merge_back: Safely merges finalized changes from the sandbox back into the
  user's original source repository.
- path_policy: A critical security component that ensures no file operation
  can escape the designated sandbox directory.
"""

from .fs_manager import (
    onboard_repo,
    create_snapshot,
    checkout_snapshot,
    rollback,
    SandboxError,
)
from .diff_utils import diff_snapshots, format_diff_for_display
from .merge_back import execute_merge, MergeResult
from .path_policy import is_path_safe

__all__ = [
    "onboard_repo",
    "create_snapshot",
    "checkout_snapshot",
    "rollback",
    "SandboxError",
    "diff_snapshots",
    "format_diff_for_display",
    "execute_merge",
    "MergeResult",
    "is_path_safe",
]
