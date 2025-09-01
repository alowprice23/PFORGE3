from __future__ import annotations
from typing import List, Dict, Any, Set, Collection

def _is_hitting_set(candidate: Set[Any], set_collection: Collection[Set[Any]]) -> bool:
    """
    Checks if a candidate set is a hitting set for a collection of sets.
    A set is a hitting set if it has a non-empty intersection with every
    set in the collection.
    """
    for s in set_collection:
        if not candidate.intersection(s):
            return False
    return True

def verify_conflict_minimality(session_log: List[Dict[str, Any]]) -> tuple[bool, List[Dict]]:
    """
    Verifies the minimality of all hitting sets from CONFLICT.FOUND events.

    A hitting set is minimal if no proper subset of it is also a hitting set.

    Args:
        session_log: A list of AMP events.

    Returns:
        A tuple containing:
        - A boolean that is True if all hitting sets are minimal.
        - A list of logs for any non-minimal sets found.
    """
    all_minimal = True
    failures = []

    for event in session_log:
        if event.get("name") == "CONFLICT.FOUND":
            payload = event.get("payload", {})
            op_id = event.get("op_id")

            # The payload should contain the hitting set and the sets it hits.
            # Assuming `violated_constraints` is a list of lists/sets.
            hitting_set = set(payload.get("hitting_set", []))
            violated_constraints = [set(c) for c in payload.get("violated_constraints", [])]

            if not hitting_set or not violated_constraints:
                continue

            # Check for minimality
            for element in hitting_set:
                # Create a proper subset by removing one element.
                subset = hitting_set - {element}
                if _is_hitting_set(subset, violated_constraints):
                    all_minimal = False
                    failures.append({
                        "op_id": op_id,
                        "hitting_set": list(hitting_set),
                        "redundant_element": element,
                        "message": "Hitting set is not minimal."
                    })
                    # No need to check other elements for this set.
                    break

    return all_minimal, failures
