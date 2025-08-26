from __future__ import annotations
import orjson
import time
from typing import Dict, Any, List
import uuid

from .signatures import sign_hmac_sha256, verify_hmac_sha256

# In a real system, the nonce store would be persistent (e.g., Redis or SQLite)
# to prevent replay attacks across restarts. For the foundational core, an
# in-memory set is sufficient to demonstrate the concept.
_USED_NONCES = set()

class InvalidCapabilityError(Exception):
    """Raised when a capability token is invalid, expired, or replayed."""
    pass

def issue_token(
    actor: str,
    scope: List[str],
    op_id: str,
    expires_in_seconds: int = 60
) -> str:
    """
    Issues a new capability token.

    A capability token is a JSON object containing the permissions (scope),
    the actor it's issued to, an expiration time, and a unique nonce to
    prevent replay attacks. The entire token is signed to prevent tampering.

    Args:
        actor: The name of the agent or user this token is for.
        scope: A list of permissions granted (e.g., ["fs:write", "exec:test"]).
        op_id: The unique operation ID this token is associated with.
        expires_in_seconds: The validity period of the token.

    Returns:
        A signed capability token string.
    """
    issued_at = int(time.time())
    expires_at = issued_at + expires_in_seconds
    nonce = str(uuid.uuid4())

    payload = {
        "actor": actor,
        "scope": sorted(scope), # Sort for deterministic serialization
        "op_id": op_id,
        "iat": issued_at,
        "exp": expires_at,
        "nonce": nonce,
    }

    # Serialize the payload and sign it
    payload_json = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    signature = sign_hmac_sha256(payload_json)

    # The final token is the payload + signature
    token = f"{payload_json.decode('utf-8')}.{signature}"
    return token

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verifies a capability token and returns its payload if valid.

    This function checks:
    1. The token's structure is valid.
    2. The signature is correct (the token hasn't been tampered with).
    3. The token has not expired.
    4. The nonce has not been used before (to prevent replay attacks).

    Args:
        token: The capability token string to verify.

    Returns:
        The payload dictionary if the token is valid.

    Raises:
        InvalidCapabilityError: If the token is invalid for any reason.
    """
    try:
        payload_json_str, signature = token.rsplit('.', 1)
    except ValueError:
        raise InvalidCapabilityError("Invalid token format.")

    # 1. Verify the signature
    if not verify_hmac_sha256(payload_json_str, signature):
        raise InvalidCapabilityError("Invalid signature.")

    payload = orjson.loads(payload_json_str)

    # 2. Check for expiration
    expires_at = payload.get("exp", 0)
    if int(time.time()) > expires_at:
        raise InvalidCapabilityError("Token has expired.")

    # 3. Check for nonce replay
    nonce = payload.get("nonce")
    if not nonce:
        raise InvalidCapabilityError("Token is missing a nonce.")
    if nonce in _USED_NONCES:
        raise InvalidCapabilityError("Token has already been used (replay attack).")

    # 4. Mark the nonce as used
    _USED_NONCES.add(nonce)

    # The nonce store should be periodically cleaned of expired nonces
    # to prevent it from growing indefinitely. This is omitted for simplicity here.

    return payload
