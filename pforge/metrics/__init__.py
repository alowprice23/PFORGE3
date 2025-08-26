"""
The Metrics package provides a centralized, standardized way of defining,
collecting, and exposing all system metrics for observability.

Modules:
- metrics_collector: Defines and exports every Prometheus metric object.
- prometheus_exporter: The FastAPI router that exposes the /metrics endpoint.
"""

from . import metrics_collector
from .prometheus_exporter import router as metrics_router

__all__ = [
    "metrics_collector",
    "metrics_router",
]
