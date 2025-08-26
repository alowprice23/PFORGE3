from __future__ import annotations
import hashlib
import os
from pathlib import Path
from typing import Union

# In a real application, this root would be configured.
# For the foundational slice, we can derive it relative to this file.
_CAS_ROOT = Path(os.environ.get("PFORGE_VAR_DIR", "pforge/var")) / "cas_objects"

class DataCorruptionError(Exception):
    """Raised when data read from the CAS does not match its hash."""
    pass

def _get_storage_path(sha256_hash: str) -> Path:
    """
    Determines the sharded storage path for a given hash.
    e.g., 'abcdef123...' -> /path/to/cas/ab/cdef123...
    """
    if len(sha256_hash) != 64:
        raise ValueError("Invalid SHA256 hash provided.")

    # Use the first 2 characters for the directory to shard files.
    # This prevents having too many files in a single directory.
    dir_name = sha256_hash[:2]
    file_name = sha256_hash[2:]

    return _CAS_ROOT / dir_name / file_name

def write_blob(data: Union[str, bytes]) -> str:
    """
    Writes a blob of data to the Content-Addressable Store.

    The data is stored at a path determined by its SHA256 hash. If the data
    already exists, this operation is a no-op.

    Args:
        data: The data to store. If string, it will be utf-8 encoded.

    Returns:
        The SHA256 hash of the data.
    """
    if isinstance(data, str):
        data_bytes = data.encode('utf-8')
    else:
        data_bytes = data

    sha256_hash = hashlib.sha256(data_bytes).hexdigest()
    storage_path = _get_storage_path(sha256_hash)

    # This is an atomic check. If the file already exists, we assume its
    # content is correct and do nothing.
    if not storage_path.exists():
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temporary file and then rename to ensure atomicity.
        temp_path = storage_path.with_suffix(".tmp")
        temp_path.write_bytes(data_bytes)
        temp_path.rename(storage_path)

    return sha256_hash

def read_blob(sha256_hash: str) -> bytes:
    """
    Reads a blob of data from the CAS.

    Args:
        sha256_hash: The hash of the blob to read.

    Returns:
        The raw byte content of the blob.

    Raises:
        FileNotFoundError: If no blob with the given hash exists.
        DataCorruptionError: If the stored data's hash does not match.
    """
    storage_path = _get_storage_path(sha256_hash)

    if not storage_path.exists():
        raise FileNotFoundError(f"No blob found with hash: {sha256_hash}")

    data_bytes = storage_path.read_bytes()

    # Verify data integrity on read.
    actual_hash = hashlib.sha256(data_bytes).hexdigest()
    if actual_hash != sha256_hash:
        raise DataCorruptionError(
            f"Data corruption detected for blob {sha256_hash}. "
            f"Actual hash was {actual_hash}."
        )

    return data_bytes
