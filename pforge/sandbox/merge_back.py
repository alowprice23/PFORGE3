from __future__ import annotations
import logging
import subprocess
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

class MergeResult(NamedTuple):
    """
    Represents the outcome of a merge operation.
    """
    success: bool
    conflict: bool
    message: str

def execute_merge(
    source_repo_path: str,
    final_commit_sha: str,
    sandbox_path: str = "pforge/workspace"
) -> MergeResult:
    """
    Merges the finalized changes from the sandbox back into the source repository.

    This function uses a safe Git-based strategy to perform the merge:
    1. It adds the sandbox as a temporary git remote to the source repo.
    2. It fetches the commits from the sandbox.
    3. It attempts to merge the final commit.
    4. It detects conflicts and aborts the merge if any occur.
    5. It cleans up by removing the temporary remote.

    Args:
        source_repo_path: The path to the user's original git repository.
        final_commit_sha: The SHA of the final, proven commit in the sandbox.
        sandbox_path: The path to the sandbox worktree, which is treated as a git repo.

    Returns:
        A MergeResult object detailing the outcome.
    """
    source_repo = Path(source_repo_path)
    sandbox_repo = Path(sandbox_path)
    remote_name = "pforge_sandbox_remote"

    if not (source_repo / ".git").is_dir():
        return MergeResult(False, False, "Source path is not a valid Git repository.")
    if not (sandbox_repo / ".git").is_dir():
        # This assumes the sandbox worktree is also a git repo.
        # fs_manager would need to ensure this.
        return MergeResult(False, False, "Sandbox path is not a valid Git repository.")

    def run_git(command: list[str], repo_path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo_path)] + command,
            capture_output=True,
            text=True
        )

    # 1. Clean up any previous temporary remote
    run_git(["remote", "remove", remote_name], source_repo)

    # 2. Add the sandbox as a temporary remote
    add_remote_result = run_git(["remote", "add", remote_name, str(sandbox_repo.resolve())], source_repo)
    if add_remote_result.returncode != 0:
        return MergeResult(False, False, f"Failed to add sandbox remote: {add_remote_result.stderr}")

    try:
        # 3. Fetch from the sandbox remote
        fetch_result = run_git(["fetch", remote_name], source_repo)
        if fetch_result.returncode != 0:
            return MergeResult(False, False, f"Failed to fetch from sandbox: {fetch_result.stderr}")

        # 4. Attempt the merge
        # We use --no-ff to create a merge commit, preserving history.
        # The final_commit_sha is what we want to merge.
        merge_result = run_git(["merge", "--no-ff", final_commit_sha, "-m", f"Merge pForge changes (commit {final_commit_sha[:7]})"], source_repo)

        if merge_result.returncode == 0:
            return MergeResult(True, False, "Merge successful.")
        else:
            # Merge failed, likely due to conflicts.
            logger.warning(f"Merge conflict detected. Stderr: {merge_result.stderr}")
            # Abort the merge to leave the user's repo clean.
            run_git(["merge", "--abort"], source_repo)
            return MergeResult(False, True, "Merge conflict detected. Operation aborted.")

    finally:
        # 5. Always clean up the temporary remote
        run_git(["remote", "remove", remote_name], source_repo)
