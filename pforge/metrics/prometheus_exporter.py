from __future__ import annotations
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# This ensures that all metrics defined in the collector are registered
# with the default Prometheus registry when this module is imported.

router = APIRouter()

@router.get(
    "/metrics",
    summary="Expose Prometheus Metrics",
    description="Provides the metrics in the Prometheus text-based format for scraping.",
    tags=["Monitoring"]
)
async def get_metrics():
    """
    This endpoint generates the latest values of all registered Prometheus
    metrics and returns them in the standard exposition format.
    """
    # The `generate_latest` function collects metrics from the default registry.
    metrics_data = generate_latest()

    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
