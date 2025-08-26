from __future__ import annotations
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import os
import jwt # PyJWT

# In a real system, the secret would be managed more securely.
JWT_SECRET = os.environ.get("PFORGE_JWT_SECRET", "default-jwt-secret")
API_KEY = os.environ.get("PFORGE_API_KEY", "default-api-key")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Identifies the user and tenant from request headers.

        This middleware checks for:
        1. A 'Bearer <token>' in the Authorization header (for JWTs).
        2. An 'X-API-Key' header (for simple, static API keys).

        It attaches 'user' and 'tenant' to `request.state` for downstream use.
        If no valid credentials are found, it defaults to an 'anonymous' user.
        """
        user = "anonymous"
        tenant = "default"

        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decode the JWT to get user and tenant info
                payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                user = payload.get("sub", user) # 'sub' is standard for subject/user
                tenant = payload.get("tenant", tenant)
            except jwt.PyJWTError:
                # Invalid JWT, proceed as anonymous
                pass

        elif api_key_header:
            # Simple static API key check
            if api_key_header == API_KEY:
                user = "api_user"
                tenant = "default" # Or derive from a different header

        # Attach the identified user and tenant to the request state
        request.state.user = user
        request.state.tenant = tenant

        response = await call_next(request)
        return response
