from __future__ import annotations
from fastapi import APIRouter

# The actual endpoint logic is defined in the metrics package to keep
# concerns separated. This file just imports and includes that router
# into the main server application.
from pforge.metrics import metrics_router

router = APIRouter()

# Include the router from the metrics exporter.
# This makes the /metrics endpoint available under the main FastAPI app.
router.include_router(metrics_router)
