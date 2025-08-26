from __future__ import annotations
from fastapi import APIRouter, HTTPException

# In a real system, you would have a dedicated service or database
# for storing and retrieving proof bundles by their operation ID.
# For the foundational slice, we'll use a simple in-memory dictionary
# as a placeholder for this database.
_PROOF_STORE = {}

router = APIRouter()

@router.get(
    "/{op_id}",
    summary="Retrieve a proof bundle by operation ID",
    tags=["Proofs"]
)
async def get_proof_bundle(op_id: str):
    """
    Fetches the full, signed proof bundle associated with a specific
    operation ID.

    This endpoint allows external auditors or the UI to inspect the
    verifiable evidence for any claim made by the pForge system.
    """

    # This is a placeholder for fetching the proof from a persistent store.
    # In a real implementation, an agent would have published the proof to a
    # database or a dedicated stream when it was created.
    proof_bundle = _PROOF_STORE.get(op_id)

    if not proof_bundle:
        raise HTTPException(
            status_code=404,
            detail=f"No proof bundle found for operation ID: {op_id}"
        )

    # The stored object should be the full, signed AMP message
    # containing the proof. We return it directly.
    return proof_bundle
