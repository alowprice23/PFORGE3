"""
Project abstraction for pForge.

This module provides a `Project` class that abstracts all file system
operations. Agents should use this class to read and write files,
rather than accessing the file system directly.
"""
from __future__ import annotations

from pathlib import Path

class Project:
    """
    Represents the project being analyzed and fixed.
    It provides a controlled interface to the file system.
    """

    def __init__(self, root_path: Path | str):
        self.root = Path(root_path).resolve()
        if not self.root.is_dir():
            raise ValueError(f"Project root does not exist or is not a directory: {self.root}")

    def read_file(self, file_path: Path | str) -> str:
        """
        Reads the content of a file within the project.

        :param file_path: Relative path to the file from the project root.
        :return: The content of the file as a string.
        """
        abs_path = self._resolve_path(file_path)
        try:
            with abs_path.open("r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found in project: {file_path}")
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    def write_file(self, file_path: Path | str, content: str):
        """
        Writes content to a file within the project.
        This will create directories if they don't exist.

        :param file_path: Relative path to the file from the project root.
        :param content: The content to write to the file.
        """
        abs_path = self._resolve_path(file_path)
        try:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            with abs_path.open("w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise IOError(f"Error writing to file {file_path}: {e}")

    def _resolve_path(self, file_path: Path | str) -> Path:
        """
        Resolves a relative path to an absolute path within the project,
        and ensures it does not escape the project root.
        """
        path = self.root.joinpath(file_path).resolve()
        if self.root not in path.parents and path != self.root:
            raise SecurityError(f"Attempted to access file outside of project root: {path}")
        return path

    def list_files(self, pattern: str = "**/*") -> list[str]:
        """
        Lists all files in the project matching a glob pattern.

        :param pattern: The glob pattern to match files (e.g., "**/*.py").
        :return: A list of relative file paths.
        """
        return [
            str(p.relative_to(self.root))
            for p in self.root.glob(pattern)
            if p.is_file()
        ]

# Example of how to use it:
#
# from pathlib import Path
# from pforge.project import Project
#
# project = Project(Path("."))
# content = project.read_file("README.md")
# project.write_file("new_file.txt", "Hello, pForge!")
