from __future__ import annotations
import os
from pathlib import Path

def is_path_safe(path_to_check: Union[str, Path], sandbox_root: Union[str, Path]) -> bool:
    """
    Verifies that a given path is safely contained within a sandbox root.

    This function is a critical security control to prevent path traversal
    attacks, where a malicious path (`../../etc/passwd`) could be used to
    access files outside the intended directory.

    It works by:
    1. Resolving both paths to their absolute, canonical form, which
       evaluates any '..' components and resolves symbolic links.
    2. Checking if the resolved path of the file is a subdirectory of (or
       the same as) the resolved sandbox root.

    Args:
        path_to_check: The path to validate.
        sandbox_root: The root directory that the path should be confined to.

    Returns:
        True if the path is safe, False otherwise.
    """
    try:
        # Resolve both paths to their absolute, real paths.
        # This is the most important step for security.
        real_sandbox_root = Path(sandbox_root).resolve(strict=True)
        real_path_to_check = Path(path_to_check).resolve(strict=True)

        # The common path between the two must be the sandbox root itself.
        # This is a robust way to check for containment.
        common_path = Path(os.path.commonpath([real_sandbox_root, real_path_to_check]))

        return common_path == real_sandbox_root

    except (FileNotFoundError, RuntimeError):
        # If a path doesn't exist or a symlink loop is detected,
        # it's considered unsafe.
        return False
    except Exception:
        # Catch any other potential filesystem errors and default to unsafe.
        return False
