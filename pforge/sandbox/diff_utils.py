from __future__ import annotations
import difflib
import orjson
from typing import Dict, Any

from pforge.storage.cas import read_blob

def diff_snapshots(commit_a_sha: str, commit_b_sha: str) -> Dict[str, Any]:
    """
    Computes a structured difference between two snapshots (commits).

    Args:
        commit_a_sha: The SHA of the "before" commit.
        commit_b_sha: The SHA of the "after" commit.

    Returns:
        A dictionary detailing the added, removed, and changed files.
    """
    # 1. Load the tree manifests for both commits
    commit_a_data = orjson.loads(read_blob(commit_a_sha))
    commit_b_data = orjson.loads(read_blob(commit_b_sha))

    tree_a_manifest = {item['path']: item for item in orjson.loads(read_blob(commit_a_data['tree']))}
    tree_b_manifest = {item['path']: item for item in orjson.loads(read_blob(commit_b_data['tree']))}

    paths_a = set(tree_a_manifest.keys())
    paths_b = set(tree_b_manifest.keys())

    # 2. Identify added, removed, and common paths
    added_paths = sorted(list(paths_b - paths_a))
    removed_paths = sorted(list(paths_a - paths_b))
    common_paths = sorted(list(paths_a & paths_b))

    # 3. For common paths, identify which ones have changed content
    changed_files = []
    for path in common_paths:
        if tree_a_manifest[path]['sha'] != tree_b_manifest[path]['sha']:
            changed_files.append({
                "path": path,
                "sha_before": tree_a_manifest[path]['sha'],
                "sha_after": tree_b_manifest[path]['sha'],
            })

    return {
        "added": added_paths,
        "removed": removed_paths,
        "changed": changed_files,
    }

def format_diff_for_display(diff: Dict[str, Any], color: bool = True) -> str:
    """
    Formats a structured diff object into a human-readable string.

    Args:
        diff: The structured diff from `diff_snapshots`.
        color: Whether to use ANSI color codes for display.

    Returns:
        A formatted string similar to `git diff --stat` and unified diffs.
    """
    output_lines = []

    # ANSI color codes
    COLOR_GREEN = "\033[92m"
    COLOR_RED = "\033[91m"
    COLOR_YELLOW = "\033[93m"
    COLOR_RESET = "\033[0m"

    if diff["added"]:
        output_lines.append("--- Added files ---")
        for path in diff["added"]:
            line = f"+ {path}"
            if color:
                line = f"{COLOR_GREEN}{line}{COLOR_RESET}"
            output_lines.append(line)
        output_lines.append("")

    if diff["removed"]:
        output_lines.append("--- Removed files ---")
        for path in diff["removed"]:
            line = f"- {path}"
            if color:
                line = f"{COLOR_RED}{line}{COLOR_RESET}"
            output_lines.append(line)
        output_lines.append("")

    if diff["changed"]:
        output_lines.append("--- Modified files ---")
        for item in diff["changed"]:
            path = item['path']
            line = f"~ {path}"
            if color:
                line = f"{COLOR_YELLOW}{line}{COLOR_RESET}"
            output_lines.append(line)

            try:
                # Generate a unified diff for text files
                content_before = read_blob(item['sha_before']).decode('utf-8').splitlines()
                content_after = read_blob(item['sha_after']).decode('utf-8').splitlines()

                unified_diff = difflib.unified_diff(
                    content_before,
                    content_after,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm=""
                )

                for diff_line in unified_diff:
                    if color:
                        if diff_line.startswith('+'):
                            output_lines.append(f"{COLOR_GREEN}{diff_line}{COLOR_RESET}")
                        elif diff_line.startswith('-'):
                            output_lines.append(f"{COLOR_RED}{diff_line}{COLOR_RESET}")
                        else:
                            output_lines.append(diff_line)
                    else:
                        output_lines.append(diff_line)
            except UnicodeDecodeError:
                output_lines.append("  (Binary file changed)")
        output_lines.append("")

    return "\n".join(output_lines)
