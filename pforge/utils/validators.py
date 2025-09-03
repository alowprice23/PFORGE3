from __future__ import annotations

def should_ignore_path(path: str) -> bool:
    return any(part.startswith('.') for part in path.split('/'))
