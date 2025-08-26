"""
The Recovery package is responsible for ensuring the operational stability
of the pForge execution environment.

It detects, diagnoses, and automatically remediates failures in prerequisites
like runtime versions, package dependencies, and service availability.

Modules:
- preflight: The main engine that orchestrates the preflight checks.
- detectors: A collection of functions that probe the environment.
- actions: A collection of functions that can repair the environment.
"""

from .preflight import PreflightEngine

__all__ = ["PreflightEngine"]
