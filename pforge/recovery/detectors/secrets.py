from __future__ import annotations
import os
from typing import Tuple

def check_api_key(service_name: str) -> Tuple[bool, dict]:
    """
    Checks for the presence of a required API key in the environment.

    It constructs the environment variable name from the service name,
    e.g., 'openai' -> 'OPENAI_API_KEY'.

    Args:
        service_name: The name of the service (e.g., 'openai', 'anthropic').

    Returns:
        A tuple containing a boolean indicating if the key is present, and a
        details dictionary.
    """
    env_var_name = f"{service_name.upper()}_API_KEY"
    api_key = os.environ.get(env_var_name)

    if api_key:
        is_ok = True
        # We only witness the presence, not the value, for security.
        witness = {"status": "present", "variable_name": env_var_name}
    else:
        is_ok = False
        witness = {"status": "missing", "variable_name": env_var_name}

    return is_ok, witness
