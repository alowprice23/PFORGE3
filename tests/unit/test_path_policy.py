import pytest
from pathlib import Path
import tempfile
import os

from pforge.sandbox.path_policy import is_path_safe

@pytest.fixture
def sandbox_root():
    """Provides a temporary directory to act as the sandbox root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir).resolve()

def test_path_is_safe_when_inside_sandbox(sandbox_root):
    """
    Tests that a path that is clearly inside the sandbox is considered safe.
    """
    safe_path = sandbox_root / "some_dir" / "some_file.txt"
    safe_path.parent.mkdir()
    safe_path.touch()

    assert is_path_safe(safe_path, sandbox_root) is True

def test_path_is_unsafe_when_outside_sandbox(sandbox_root):
    """
    Tests that a path outside the sandbox is considered unsafe.
    """
    # Create a file in a completely different temporary directory
    with tempfile.TemporaryDirectory() as other_dir:
        unsafe_path = Path(other_dir) / "secret_file.txt"
        unsafe_path.touch()

        assert is_path_safe(unsafe_path, sandbox_root) is False

def test_path_traversal_is_unsafe(sandbox_root):
    """
    Tests that a path attempting to traverse upwards ('..') is unsafe.
    """
    # This path looks like it's inside, but '..' takes it out.
    traversal_path = sandbox_root / "some_dir" / ".." / ".." / "another_file.txt"

    # The is_path_safe function should resolve this to its real path
    # and detect that it's outside the sandbox root.
    assert is_path_safe(traversal_path, sandbox_root) is False

def test_symlink_escape_is_unsafe(sandbox_root):
    """
    Tests that a symbolic link pointing outside the sandbox is detected as unsafe.
    """
    # Create a target for the symlink outside the sandbox
    with tempfile.TemporaryDirectory() as other_dir:
        secret_file = Path(other_dir) / "secret.txt"
        secret_file.touch()

        # Create a symlink inside the sandbox that points to the secret file
        symlink_path = sandbox_root / "link_to_secret"
        os.symlink(secret_file, symlink_path)

        # is_path_safe should resolve the symlink and see that its real path
        # is outside the sandbox.
        assert is_path_safe(symlink_path, sandbox_root) is False

def test_symlink_inside_sandbox_is_safe(sandbox_root):
    """
    Tests that a symlink pointing to another file *inside* the sandbox is safe.
    """
    target_file = sandbox_root / "real_file.txt"
    target_file.touch()

    symlink_path = sandbox_root / "link_to_real_file"
    os.symlink(target_file, symlink_path)

    assert is_path_safe(symlink_path, sandbox_root) is True

def test_nonexistent_path_is_unsafe(sandbox_root):
    """
    Tests that a path that does not exist is considered unsafe.
    """
    nonexistent_path = sandbox_root / "does" / "not" / "exist.txt"
    assert is_path_safe(nonexistent_path, sandbox_root) is False
