from __future__ import annotations
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List

from pforge.storage.cas import write_blob, read_blob
from .path_policy import is_path_safe

logger = logging.getLogger(__name__)

# This would be configured, but we'll define a default for the slice.
_SANDBOX_ROOT = Path(os.environ.get("PFORGE_SANDBOX_DIR", "pforge/workspace"))
_CAS_ROOT = Path(os.environ.get("PFORGE_VAR_DIR", "pforge/var")) / "cas_objects" # This should align with storage/cas.py

class SandboxError(Exception):
    """Base exception for sandbox operations."""
    pass

def _create_tree_object(worktree_path: Path) -> str:
    """
    Creates a "tree" object in the CAS from a worktree directory.
    A tree object is a manifest mapping file paths to their content hashes.
    """
    entries = []
    for root, _, files in os.walk(worktree_path):
        for filename in files:
            full_path = Path(root) / filename
            if not is_path_safe(full_path, worktree_path):
                continue # Skip files outside the worktree (e.g., symlinks)

            relative_path = str(full_path.relative_to(worktree_path))
            file_bytes = full_path.read_bytes()
            blob_sha = write_blob(file_bytes)

            entries.append({
                "path": relative_path,
                "sha": blob_sha,
                "mode": full_path.stat().st_mode,
            })

    # The tree itself is a JSON blob, stored in the CAS.
    # Sorting ensures the hash is deterministic.
    tree_content = sorted(entries, key=lambda x: x['path'])
    return write_blob(orjson.dumps(tree_content))

def onboard_repo(source_path: str) -> str:
    """
    Onboards a source repository into the pForge system.

    This involves copying all files into the CAS and creating an initial
    commit object representing the repository's state.

    Args:
        source_path: The local path to the repository to onboard.

    Returns:
        The SHA of the initial commit object.
    """
    source_path = Path(source_path)
    if not source_path.is_dir():
        raise SandboxError(f"Source path '{source_path}' is not a valid directory.")

    logger.info(f"Onboarding repository from '{source_path}'...")

    # Create the initial tree from the source files
    tree_sha = _create_tree_object(source_path)

    # Create the first commit object
    commit_data = {
        "tree": tree_sha,
        "parents": [],
        "message": "Initial import",
        "author": "pForge Onboarder",
        "timestamp": time.time(),
    }
    commit_sha = write_blob(orjson.dumps(commit_data))

    logger.info(f"Onboarding complete. Initial commit SHA: {commit_sha}")
    return commit_sha

def create_snapshot(worktree_path: str, parent_commit_sha: str, message: str) -> str:
    """
    Creates a new snapshot (commit) from the current state of a worktree.
    """
    worktree_path = Path(worktree_path)
    tree_sha = _create_tree_object(worktree_path)

    commit_data = {
        "tree": tree_sha,
        "parents": [parent_commit_sha],
        "message": message,
        "author": "pForge Agent",
        "timestamp": time.time(),
    }
    commit_sha = write_blob(orjson.dumps(commit_data))
    return commit_sha

def checkout_snapshot(commit_sha: str, target_worktree_path: str):
    """
    "Hydrates" a worktree directory with the files from a specific snapshot.
    Any existing content in the target directory is removed.
    """
    target_path = Path(target_worktree_path)
    if target_path.exists():
        shutil.rmtree(target_path)
    target_path.mkdir(parents=True)

    # 1. Read the commit object to find the tree hash
    commit_data = orjson.loads(read_blob(commit_sha))
    tree_sha = commit_data["tree"]

    # 2. Read the tree object to get the file manifest
    tree_manifest = orjson.loads(read_blob(tree_sha))

    # 3. Write each file to the worktree
    for entry in tree_manifest:
        file_path = target_path / entry["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_content = read_blob(entry["sha"])
        file_path.write_bytes(file_content)
        os.chmod(file_path, entry["mode"])

    logger.info(f"Checked out snapshot for commit {commit_sha} to '{target_path}'.")

def rollback(commit_sha: str, worktree_path: str):
    """Convenience function to revert a worktree to a specific snapshot."""
    logger.warning(f"Rolling back worktree '{worktree_path}' to commit {commit_sha}.")
    checkout_snapshot(commit_sha, worktree_path)
