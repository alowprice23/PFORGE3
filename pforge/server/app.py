from __future__ import annotations
from fastapi import FastAPI
import logging

from .middleware.auth import AuthMiddleware
from .middleware.authz import AuthorizationMiddleware
from .middleware.budget_guard import BudgetGuardMiddleware
from .middleware.redaction import RedactionMiddleware
from .middleware.throttle import ThrottleMiddleware
from .routes import chat, files, metrics, proofs
from .websocket.consumer import attach_ws_to_app
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="pForge API Server",
    description="The main API for interacting with the pForge puzzle-solving system.",
    version="3.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# --- Middleware Stack ---
# The order is important: auth -> authz -> budget -> throttle -> redaction
app.add_middleware(AuthMiddleware)
app.add_middleware(AuthorizationMiddleware)
app.add_middleware(BudgetGuardMiddleware)
app.add_middleware(ThrottleMiddleware)
app.add_middleware(RedactionMiddleware)


# --- API Routers ---
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(metrics.router, prefix="/api", tags=["Monitoring"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(proofs.router, prefix="/api/proofs", tags=["Proofs"])

# --- WebSocket ---
attach_ws_to_app(app)

@app.get("/api/healthz", tags=["Health"])
async def health_check():
    """
    A simple health check endpoint to confirm the server is running.
    """
    return {"status": "ok"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logging.info("pForge API server is starting up...")
    # Initialize orchestrator, etc.
    yield
    # Code to run on shutdown
    logging.info("pforge API server is shutting down...")
    # Clean up resources

app.router.lifespan_context = lifespan
