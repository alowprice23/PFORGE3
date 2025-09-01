from __future__ import annotations
from typing import Dict

def compute_task_priority(payload: Dict) -> float:
    """
    Calculates the priority of a fix task based on a simplified formula.
    P = Impact / Effort

    - Impact is high for failing tests.
    - Effort is estimated from the length of the traceback.
    - Frequency and Risk are currently omitted for simplicity.

    Args:
        payload: The payload of the TESTS_FAILED message.

    Returns:
        The calculated priority score, normalized between 0 and 1.
    """
    # Simplified Impact: Failing tests are high impact.
    impact = 1.0

    # Simplified Effort: Estimate from traceback length.
    # A longer traceback might indicate a more complex issue.
    traceback = ""
    if payload.get("failed_tests"):
        traceback = payload["failed_tests"][0].get("traceback", "")

    # Normalize effort: 1.0 for no traceback, increasing with length.
    # We add 1 to avoid division by zero and to represent a baseline effort.
    effort = 1.0 + len(traceback) / 1000.0

    # Simplified formula: Priority = Impact / Effort
    priority = impact / effort

    # Clamp the priority to a [0, 1] range.
    return max(0.0, min(1.0, priority))
