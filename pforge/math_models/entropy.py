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


def calculate_shannon_entropy(data: str) -> float:
    """
    Calculates the Shannon entropy of a string.
    """
    if not data:
        return 0.0

    entropy = 0.0
    for x in range(256):
        p_x = float(data.count(chr(x))) / len(data)
        if p_x > 0:
            entropy += -p_x * math.log2(p_x)

    return entropy


def is_potential_secret(
    text: str,
    entropy_threshold: float = 4.5,
    min_length: int = 20,
) -> bool:
    """
    Determines if a string is a potential secret based on length and entropy.
    """
    if len(text) < min_length:
        return False

    entropy = calculate_shannon_entropy(text)
    return entropy > entropy_threshold
