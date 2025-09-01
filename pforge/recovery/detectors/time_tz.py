from __future__ import annotations
import time
from typing import Tuple

def check_timezone(expected_tz: str = "UTC") -> Tuple[bool, dict]:
    """
    Detects non-deterministic timezone configurations by checking if the
    system timezone is set to the expected value (usually UTC).

    Args:
        expected_tz: The expected timezone name (e.g., 'UTC', 'EST').

    Returns:
        A tuple containing a boolean indicating if the check passed, and a
        details dictionary.
    """
    # time.tzname contains a tuple of non-DST and DST time zone names.
    # We check if the expected TZ is either of them.
    # For UTC, both are 'UTC'.
    actual_tz = time.tzname
    is_ok = expected_tz in actual_tz

    witness = {
        "expected": expected_tz,
        "actual": actual_tz[0] if actual_tz[0] == actual_tz[1] else f"{actual_tz[0]}/{actual_tz[1]}",
    }

    return is_ok, witness
