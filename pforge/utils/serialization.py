from __future__ import annotations
import json
from typing import Any

def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))
