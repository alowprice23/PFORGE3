import subprocess

def run_tests(directory: str = "."):
    """Runs tests in the specified directory."""
    result = subprocess.run(["pytest", directory], capture_output=True, text=True)
    return result.stdout + result.stderr

import os

def list_files(directory: str = "."):
    """Lists files in the specified directory."""
    return os.listdir(directory)

def read_file(filepath: str):
    """Reads the content of the specified file."""
    with open(filepath, "r") as f:
        return f.read()

def apply_patch(patch_content: str):
    """Applies a patch to the codebase."""
    with open("patch.diff", "w") as f:
        f.write(patch_content)
    result = subprocess.run(["git", "apply", "patch.diff"], capture_output=True, text=True)
    os.remove("patch.diff")
    return result.stdout + result.stderr
