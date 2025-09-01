from __future__ import annotations
import re
from typing import List

DENY_LIST = [
    r'\.env',
    r'id_rsa',
    r'keychain',
    r'config/creds',
]

def is_sensitive_path(path: str) -> bool:
    return any(re.search(pattern, path) for pattern in DENY_LIST)
