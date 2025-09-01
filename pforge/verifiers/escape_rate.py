from __future__ import annotations
from typing import List, Dict, Any

def calculate_escape_rate(session_log: List[Dict[str, Any]]) -> float:
    """
    Measures the escape rate of the targeted test selection.

    The escape rate is the fraction of times that a bug was missed by the
    targeted tests but caught by the full audit run.

    Args:
        session_log: A list of AMP events.

    Returns:
        The calculated escape rate, from 0.0 to 1.0.
    """
    total_patches_with_targeted_pass = 0
    escaped_bugs = 0

    for i, event in enumerate(session_log):
        if event.get("name") == "FIX.PATCH_APPLIED":
            op_id = event.get("op_id")
            targeted_pass = False
            full_audit_failed = False

            # Search for the outcomes of this patch
            for next_event in session_log[i+1:]:
                if next_event.get("op_id") != op_id or next_event.get("name") != "SPEC.CHECKED":
                    continue

                payload = next_event.get("payload", {})
                check_type = payload.get("type")
                is_satisfied = payload.get("is_satisfied")

                if check_type == 'targeted' and is_satisfied:
                    targeted_pass = True

                if check_type == 'full_audit' and not is_satisfied:
                    full_audit_failed = True

                # If we've found a targeted pass, we can stop looking for that
                # and just need the full audit result.
                if targeted_pass and full_audit_failed:
                    break

            if targeted_pass:
                total_patches_with_targeted_pass += 1
                if full_audit_failed:
                    escaped_bugs += 1

    if total_patches_with_targeted_pass == 0:
        return 0.0  # No targeted tests passed, so no escapes.

    return escaped_bugs / total_patches_with_targeted_pass
