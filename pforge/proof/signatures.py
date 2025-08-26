from __future__ import annotations
import hmac
import hashlib
import os
from typing import Union

# For a production system, you would use a proper key management system.
# For local-only mode, we can use a stable secret from an environment variable.
_HMAC_SECRET = os.environ.get("PFORGE_HMAC_SECRET", "pforge-local-secret-key").encode('utf-8')

def sign_hmac_sha256(data: Union[str, bytes]) -> str:
    """
    Signs the given data using HMAC-SHA256 with a shared secret.

    Args:
        data: The data to sign, either as a string or bytes.

    Returns:
        A hex-encoded signature string.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    signature = hmac.new(_HMAC_SECRET, data, hashlib.sha256).hexdigest()
    return signature

def verify_hmac_sha256(data: Union[str, bytes], signature: str) -> bool:
    """
    Verifies a signature against the given data using HMAC-SHA256.

    Args:
        data: The data that was signed.
        signature: The hex-encoded signature to verify.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    expected_signature = sign_hmac_sha256(data)

    # Use hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)

# In a full implementation, you would add functions for asymmetric cryptography
# like Ed25519 here. For the foundational core, HMAC is sufficient.

def sign_ed25519(data: bytes, private_key: bytes) -> bytes:
    """
    Placeholder for signing data with an Ed25519 private key.
    Requires the 'cryptography' package.
    """
    # from cryptography.hazmat.primitives.asymmetric import ed25519
    # private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
    # signature = private_key_obj.sign(data)
    # return signature
    raise NotImplementedError("Ed25519 signing is not implemented in the foundational core.")

def verify_ed25519(data: bytes, signature: bytes, public_key: bytes) -> bool:
    """
    Placeholder for verifying an Ed25519 signature.
    """
    # from cryptography.hazmat.primitives.asymmetric import ed25519
    # from cryptography.exceptions import InvalidSignature
    # public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
    # try:
    #     public_key_obj.verify(signature, data)
    #     return True
    # except InvalidSignature:
    #     return False
    raise NotImplementedError("Ed25519 verification is not implemented in the foundational core.")
