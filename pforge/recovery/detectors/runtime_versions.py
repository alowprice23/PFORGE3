from __future__ import annotations
import sys
from typing import Tuple

def check_python_version(major: int = 3, minor: int = 11) -> Tuple[bool, dict]:
    """
    Checks if the current Python interpreter meets the minimum version requirement.
    """
    is_ok = sys.version_info.major == major and sys.version_info.minor >= minor
    witness = {
        "expected": f">={major}.{minor}",
        "actual": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    }
    return is_ok, witness
