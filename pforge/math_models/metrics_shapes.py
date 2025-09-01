# pforge/math_models/metrics_shapes.py
"""
This module contains the data classes for the metrics of the system.
"""

from dataclasses import dataclass

@dataclass
class Efficiency:
    """Data class for the efficiency metric."""
    value: float

@dataclass
class Entropy:
    """Data class for the entropy metric."""
    value: float

@dataclass
class Priority:
    """Data class for the priority metric."""
    value: float
