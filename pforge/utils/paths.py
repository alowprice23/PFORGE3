from __future__ import annotations
from pathlib import Path

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
