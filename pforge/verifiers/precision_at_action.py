from __future__ import annotations
from typing import List, Dict, Any

def calculate_precision_at_action(session_log: List[Dict[str, Any]]) -> float:
    """
    Recomputes the Precision@Action KPI from a session log.

    Precision@Action is defined as the fraction of applied patches that
    successfully fixed a blocking constraint without introducing new ones.

    This verifier looks for a `FIX.PATCH_APPLIED` event and then finds the
    next `SPEC.CHECKED` event to determine the outcome.

    Args:
        session_log: A list of AMP events, where each event is a dictionary.

    Returns:
        The calculated Precision@Action score, from 0.0 to 1.0.
    """
    applied_patches = 0
    successful_patches = 0

    for i, event in enumerate(session_log):
        if event.get("name") == "FIX.PATCH_APPLIED":
            applied_patches += 1
            op_id = event.get("op_id")

            # Find the corresponding SPEC.CHECKED event.
            for next_event in session_log[i+1:]:
                if next_event.get("op_id") == op_id and next_event.get("name") == "SPEC.CHECKED":
                    # A successful patch is one where the spec is now satisfied.
                    if next_event.get("payload", {}).get("is_satisfied", False):
                        successful_patches += 1
                    break  # Move to the next patch event

    if applied_patches == 0:
        return 1.0  # Or 0.0, depending on definition. 1.0 implies "no errors".

    return successful_patches / applied_patches
