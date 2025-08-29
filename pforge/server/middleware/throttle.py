from __future__ import annotations
import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

# This is a simple in-memory store. For a multi-process or multi-server
# setup, this would need to be backed by a shared store like Redis.
_REQUEST_TIMESTAMPS: Dict[str, List[float]] = defaultdict(list)

class ThrottleMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Provides simple, IP-based rate limiting using a sliding window.
        """
        # Use the client's host IP as the identifier.
        # In a production setup behind a proxy, you would need to trust
        # headers like 'X-Forwarded-For'.
        client_ip = request.client.host if request.client else "unknown"

        current_time = time.time()

        # Get the list of timestamps for this IP
        timestamps = _REQUEST_TIMESTAMPS[client_ip]

        # Remove timestamps that are older than the 60-second window
        window_start = current_time - 60
        # This is more efficient than creating a new list every time
        while timestamps and timestamps[0] < window_start:
            timestamps.pop(0)

        # If the number of requests in the window exceeds the limit, reject.
        if len(timestamps) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests. Please try again later."
            )

        # Add the current request's timestamp to the list
        timestamps.append(current_time)

        response = await call_next(request)
        return response
