"""
This package contains the individual sensor functions (detectors) that
probe the environment for specific misconfigurations or failures.

Each detector should be a simple function that returns a boolean success
flag and a dictionary of witness data.
"""

from . import runtime_versions

__all__ = ["runtime_versions"]
