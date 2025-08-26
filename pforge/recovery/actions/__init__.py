"""
This package contains the individual idempotent remediation functions (actions)
that can repair a broken environment.

Each action should perform a single, verifiable fix and ideally emit a
RECOVERY.* proof event upon successful completion.
"""

# This directory will contain modules like env_relock.py, pkg_resolve.py, etc.
# For the foundational slice, it can be empty.
