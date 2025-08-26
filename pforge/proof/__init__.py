"""
The Proof package is the cryptographic and logical foundation of trust
in the pForge system.

It provides the tools and data structures for creating, signing, verifying,
and managing the verifiable artifacts that underpin the "Proof or It Didn't
Happen" design principle.

Modules:
- bundle: Defines the canonical `ProofBundle` model.
- signatures: Provides cryptographic signing and verification functions.
- capabilities: Implements the capability-based authorization token system.
- verifier: The backtesting engine to verify historical proofs.
- redaction: A pipeline for scrubbing sensitive data from proofs and logs.
- backtest_cli: The user-facing command-line interface for the verifier.
"""

from .bundle import ProofBundle, assemble_proof_bundle
from .signatures import sign_hmac_sha256, verify_hmac_sha256
from .capabilities import issue_token, verify_token, InvalidCapabilityError
from .verifier import verify_proof_bundle, VerificationResult
from .redaction import scrub, RedactionReport

__all__ = [
    "ProofBundle",
    "assemble_proof_bundle",
    "sign_hmac_sha256",
    "verify_hmac_sha256",
    "issue_token",
    "verify_token",
    "InvalidCapabilityError",
    "verify_proof_bundle",
    "VerificationResult",
    "scrub",
    "RedactionReport",
]
