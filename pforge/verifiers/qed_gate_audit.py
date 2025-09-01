from __future__ import annotations
from typing import List, Dict, Any, Set

def audit_qed_gates(session_log: List[Dict[str, Any]]) -> tuple[bool, List[Dict]]:
    """
    Audits all QED.EMITTED events in a log to ensure gates were met.

    For each QED event, it works backwards to verify that the required
    gates (spec satisfied, stability, no open conflicts, full audit)
    were passed within the same operation context.

    Args:
        session_log: A list of AMP events.

    Returns:
        A tuple containing:
        - A boolean that is True if all QED events are valid.
        - A list of logs for any invalid QED events found.
    """
    all_valid = True
    failures = []

    for i, event in enumerate(session_log):
        if event.get("name") == "QED.EMITTED":
            op_id = event.get("op_id")

            # Define the gates that need to be passed.
            gates = {
                "spec_satisfied": False,
                "stability_ok": False,
                "no_open_conflicts": False,
                "full_audit_run": False,
            }

            # Search backwards from the QED event for gate passes.
            for prev_event in reversed(session_log[:i]):
                # Stop searching once we've left the operation context.
                if prev_event.get("op_id") != op_id:
                    break

                event_name = prev_event.get("name")
                payload = prev_event.get("payload", {})

                if event_name == "SPEC.CHECKED" and payload.get("is_satisfied"):
                    gates["spec_satisfied"] = True
                    if payload.get("type") == "full_audit":
                        gates["full_audit_run"] = True

                if event_name == "STABILITY.CHECKED" and payload.get("is_stable"):
                    gates["stability_ok"] = True

                if event_name == "CONFLICT.CHECKED" and not payload.get("has_open_conflicts"):
                    gates["no_open_conflicts"] = True

                # If all gates are found, we can stop searching.
                if all(gates.values()):
                    break

            if not all(gates.values()):
                all_valid = False
                failures.append({
                    "op_id": op_id,
                    "qed_event_index": i,
                    "missing_gates": [gate for gate, passed in gates.items() if not passed],
                })

    return all_valid, failures
