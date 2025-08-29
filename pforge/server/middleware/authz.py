from __future__ import annotations
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from pforge.proof.capabilities import verify_token, InvalidCapabilityError

class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Enforces capability-based authorization for specific routes.

        This middleware looks for an 'X-Capability-Token' header on requests
        that are marked as requiring authorization. It verifies the token's
        validity, scope, and nonce.
        """

        # In a real application, you would have a more sophisticated way
        # to mark which routes require which capabilities. For now, we'll
        # assume that if the header is present, we should check it.

        token = request.headers.get("X-Capability-Token")

        if token:
            try:
                # The verify_token function checks the signature, expiration,
                # and nonce replay.
                payload = verify_token(token)

                # Attach the verified capabilities to the request state
                # so the endpoint handler can perform fine-grained checks.
                request.state.capabilities = payload.get("scope", [])

            except InvalidCapabilityError as e:
                # If the token is invalid for any reason, deny the request.
                raise HTTPException(
                    status_code=403,
                    detail=f"Forbidden: Invalid capability token - {e}"
                )

        response = await call_next(request)
        return response
