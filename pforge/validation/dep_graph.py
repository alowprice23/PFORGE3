from __future__ import annotations
import ast
import os
from pathlib import Path
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class DependencyGraph:
    """
    Builds and represents the module dependency graph of a Python project.
    """
    def __init__(self):
        # The graph is represented as an adjacency list:
        # { "module.a": {"module.b", "module.c"} }
        # This means module.a imports module.b and module.c.
        self.graph: Dict[str, Set[str]] = {}

    def build_from_path(self, source_root: Path):
        """
        Scans all Python files in a directory and builds the dependency graph.
        """
        self.graph = {}
        py_files = list(source_root.rglob("*.py"))

        for file_path in py_files:
            module_name = self._file_path_to_module_name(file_path, source_root)
            if module_name:
                self.graph[module_name] = self._find_imports(file_path, source_root)

        logger.info(f"Built dependency graph with {len(self.graph)} modules.")

    def _file_path_to_module_name(self, file_path: Path, source_root: Path) -> str | None:
        """Converts a file path to a Python module name."""
        try:
            relative_path = file_path.relative_to(source_root)
            # Remove .py extension and replace / with .
            return str(relative_path).replace(".py", "").replace(os.sep, ".")
        except ValueError:
            return None

    def _find_imports(self, file_path: Path, source_root: Path) -> Set[str]:
        """
        Parses a Python file to find all imported modules.
        """
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Could not parse imports from {file_path}: {e}")

        return imports

    def get_reverse_closure(self, changed_modules: Set[str]) -> Set[str]:
        """
        Computes the reverse dependency closure for a set of changed modules.

        This finds all modules that directly or indirectly depend on any of
        the changed modules.

        Args:
            changed_modules: A set of module names that have changed.

        Returns:
            A set of module names that are affected by the changes.
        """
        reverse_graph: Dict[str, Set[str]] = {module: set() for module in self.graph}
        for module, dependencies in self.graph.items():
            for dep in dependencies:
                if dep in reverse_graph:
                    reverse_graph[dep].add(module)

        closure = set()
        queue = list(changed_modules)

        while queue:
            module = queue.pop(0)
            if module in closure:
                continue
            closure.add(module)

            if module in reverse_graph:
                for dependent in reverse_graph[module]:
                    if dependent not in closure:
                        queue.append(dependent)

        return closure
