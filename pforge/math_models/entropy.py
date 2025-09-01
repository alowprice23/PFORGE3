from __future__ import annotations
import math

def calculate_entropy(num_failed: int, num_passed: int) -> float:
    """
    Calculates the Shannon entropy of the test results.
    """
    total = num_failed + num_passed
    if total == 0:
        return 0.0

    p_fail = num_failed / total
    p_pass = num_passed / total

    entropy = 0.0
    if p_fail > 0:
        entropy -= p_fail * math.log2(p_fail)
    if p_pass > 0:
        entropy -= p_pass * math.log2(p_pass)

    return entropy
