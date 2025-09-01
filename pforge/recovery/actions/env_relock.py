from __future__ import annotations
import hashlib
from pathlib import Path

def relock_environment(
    requirements_path: str | Path = "pforge/requirements.txt",
    lock_file_path: str | Path = "pforge/venv_lock.sha",
) -> dict:
    """
    Simulates re-locking the environment by creating a lock file containing
    the hash of the requirements file.

    This serves as a proof that the lock is consistent with the requirements.

    Args:
        requirements_path: The path to the requirements file (e.g., requirements.txt).
        lock_file_path: The path where the lock file will be created.

    Returns:
        A dictionary containing a proof of the action taken.
    """
    try:
        req_path = Path(requirements_path)
        lock_path = Path(lock_file_path)

        # Calculate the hash of the requirements file.
        req_content = req_path.read_bytes()
        sha256_hash = hashlib.sha256(req_content).hexdigest()

        # Write the hash to the lock file.
        lock_path.write_text(f"{sha256_hash}\n")

        proof = {
            "action": "relock_environment",
            "status": "success",
            "requirements_file": str(req_path),
            "lock_file": str(lock_path),
            "lock_hash": sha256_hash,
        }
        return proof
    except FileNotFoundError as e:
        return {"action": "relock_environment", "status": "error", "error": f"File not found: {e.filename}"}
    except Exception as e:
        return {"action": "relock_environment", "status": "error", "error": str(e)}
