from __future__ import annotations
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, StreamingResponse
import orjson

from pforge.proof.redaction import scrub

class RedactionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        A response middleware that scrubs sensitive data from JSON responses.
        """
        response = await call_next(request)

        # We only want to process JSON responses, not streaming responses or others.
        if isinstance(response, StreamingResponse) or "application/json" not in response.headers.get("content-type", ""):
            return response

        # Get the response body. This is a bit tricky with FastAPI/Starlette.
        if hasattr(response, 'body'):
            response_body = response.body
        else:
            response_body = b""

        if not response_body:
            return response

        try:
            data = orjson.loads(response_body)

            # Use the redaction service to scrub the data
            scrubbed_data, report = scrub(data)

            # If any redactions occurred, we can log it or add a header.
            if report.total_redactions > 0:
                # This is a good place to add a custom header to indicate redaction.
                response.headers["X-Redaction-Count"] = str(report.total_redactions)

            # Create a new response with the scrubbed body
            return Response(
                content=orjson.dumps(scrubbed_data),
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except orjson.JSONDecodeError:
            # If the body isn't valid JSON, return it as is.
            return response
