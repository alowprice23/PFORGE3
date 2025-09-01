from __future__ import annotations
from pathlib import Path

def should_ignore_path(path: str) -> bool:
    return any(part.startswith('.') for part in path.split('/'))
