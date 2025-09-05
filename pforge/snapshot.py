import shutil
import tempfile
from pathlib import Path

from .project import Project

class ProjectSnapshot:
    """
    Manages a temporary, sandboxed copy of a project for safe modifications and testing.
    """
    def __init__(self, original_project: Project):
        self.original_project = original_project
        self._temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self._temp_dir.name)
        self.project: Project | None = None

    def __enter__(self):
        # Copy the original project directory to the temporary directory
        shutil.copytree(self.original_project.root, self.path, dirs_exist_ok=True)
        # Create a new Project instance pointing to the sandbox
        self.project = Project(self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # The TemporaryDirectory context manager will clean itself up
        pass

    def commit(self, relative_path: Path):
        """Copies a modified file from the snapshot back to the original project."""
        source_file = self.path / relative_path
        destination_file = self.original_project.root / relative_path
        shutil.copy2(source_file, destination_file)
