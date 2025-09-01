from __future__ import annotations
import hashlib
import os
from pathlib import Path
from typing import Union, List, Dict, Optional

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

    dir_name = sha256_hash[:2]
    file_name = sha256_hash[2:]
    return _CAS_ROOT / dir_name / file_name

def write_blob(data: Union[str, bytes]) -> str:
    """
    Writes a blob of data to the Content-Addressable Store.
    """
    if isinstance(data, str):
        data_bytes = data.encode('utf-8')
    else:
        data_bytes = data

    sha256_hash = hashlib.sha256(data_bytes).hexdigest()
    storage_path = _get_storage_path(sha256_hash)

    if not storage_path.exists():
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = storage_path.with_suffix(".tmp")
        temp_path.write_bytes(data_bytes)
        temp_path.rename(storage_path)

    return sha256_hash

def read_blob(sha256_hash: str) -> bytes:
    """
    Reads a blob of data from the CAS.
    """
    storage_path = _get_storage_path(sha256_hash)

    if not storage_path.exists():
        raise FileNotFoundError(f"No blob found with hash: {sha256_hash}")

    data_bytes = storage_path.read_bytes()
    actual_hash = hashlib.sha256(data_bytes).hexdigest()
    if actual_hash != sha256_hash:
        raise DataCorruptionError(f"Data corruption for blob {sha256_hash}")

    return data_bytes

def write_tree(entries: List[Dict[str, str]]) -> str:
    """
    Takes a list of file entries (path, mode, hash) and creates a tree object.
    The format is similar to Git's tree object: `mode type hash\tpath`.
    """
    # Sort entries for a deterministic hash.
    entries.sort(key=lambda x: x['path'])

    tree_content = ""
    for entry in entries:
        # Assuming all entries are blobs for now.
        line = f"{entry['mode']} blob {entry['hash']}\t{entry['path']}\n"
        tree_content += line

    return write_blob(tree_content)

def read_tree(sha256_hash: str) -> List[Dict[str, str]]:
    """
    Retrieves a tree object by its hash and parses it.
    """
    tree_blob = read_blob(sha256_hash).decode('utf-8')
    entries = []
    for line in tree_blob.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        meta, path = parts[0], parts[1]
        mode, type, hash_val = meta.split(' ')
        entries.append({'mode': mode, 'type': type, 'hash': hash_val, 'path': path})
    return entries

def write_commit(tree_hash: str, parent_hash: Optional[str], message: str = "") -> str:
    """
    Creates a commit object that points to a tree and an optional parent commit.
    """
    commit_content = f"tree {tree_hash}\n"
    if parent_hash:
        commit_content += f"parent {parent_hash}\n"
    commit_content += f"\n{message}"

    return write_blob(commit_content)

def read_commit(sha256_hash: str) -> Dict[str, str]:
    """
    Retrieves a commit object by its hash and parses it.
    """
    commit_blob = read_blob(sha256_hash).decode('utf-8')
    lines = commit_blob.split('\n')

    commit_data = {}
    headers_done = False
    message_lines = []

    for line in lines:
        if not line and not headers_done:
            headers_done = True
            continue

        if not headers_done:
            key, value = line.split(' ', 1)
            commit_data[key] = value
        else:
            message_lines.append(line)

    commit_data['message'] = '\n'.join(message_lines)
    return commit_data
