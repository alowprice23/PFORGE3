from __future__ import annotations
import logging
from pathlib import Path
from typing import Set, List

import libcst as cst
import networkx as nx

logger = logging.getLogger(__name__)

class _ImportVisitor(cst.CSTVisitor):
    """A LibCST visitor to find all imports in a Python file."""
    def __init__(self, module_path: Path, project_root: Path):
        self.module_path = module_path
        self.project_root = project_root
        self.imports: Set[Path] = set()

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            self._resolve_import(alias.name.value)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module:
            self._resolve_import(node.module.value)

    def _resolve_import(self, import_str: str) -> None:
        """Resolves an import string to a file path."""
        # This is a simplified resolver. A real implementation would need to handle
        # relative imports, aliases, and complex package structures more robustly.
        try:
            # Convert import string like 'pforge.agents.base_agent' to a path
            # relative to the project root.
            possible_path = Path(self.project_root, *import_str.split('.'))

            # Check if it resolves to a .py file or a package directory
            if possible_path.with_suffix(".py").exists():
                self.imports.add(possible_path.with_suffix(".py").resolve())
            elif (possible_path / "__init__.py").exists():
                self.imports.add((possible_path / "__init__.py").resolve())

        except Exception as e:
            logger.debug(f"Could not resolve import '{import_str}' in {self.module_path}: {e}")


class DependencyGraph:
    """Builds and queries an import dependency graph for a project."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.graph = nx.DiGraph()
        self.build_graph()

    def build_graph(self) -> None:
        """Scans the project and builds the dependency graph."""
        logger.info("Building dependency graph...")
        # Clear the old graph before building a new one
        self.graph.clear()
        py_files = list(self.project_root.rglob("*.py"))

        for file_path in py_files:
            # Normalize file paths to be relative to the root for consistent node names
            relative_path = file_path.relative_to(self.project_root)
            self.graph.add_node(str(relative_path))

            try:
                content = file_path.read_text(encoding='utf-8')
                tree = cst.parse_module(content)
                visitor = _ImportVisitor(file_path, self.project_root)
                tree.visit(visitor)

                for imported_path in visitor.imports:
                    if imported_path.is_relative_to(self.project_root):
                        imported_relative_path = imported_path.relative_to(self.project_root)
                        # Add an edge from the current file to the file it imports
                        self.graph.add_edge(str(relative_path), str(imported_relative_path))

            except (cst.ParserSyntaxError, FileNotFoundError, UnicodeDecodeError) as e:
                logger.error(f"Could not parse {file_path}: {e}")

        logger.info(f"Dependency graph built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")

    def get_reverse_dependencies(self, file_path: str | Path) -> Set[Path]:
        """
        Gets all files that import the given file, directly or indirectly.
        This is the reverse dependency closure.
        """
        relative_path = str(Path(file_path).relative_to(self.project_root))
        if relative_path not in self.graph:
            return set()

        # nx.ancestors finds all nodes that have a path to the given node.
        # In our graph, if A imports B, the edge is A -> B.
        # So, the ancestors of B are all the files that import B.
        ancestors = nx.ancestors(self.graph, relative_path)
        return {self.project_root / p for p in ancestors}

    def get_forward_dependencies(self, file_path: str | Path) -> Set[Path]:
        """
        Gets all files that are imported by the given file, directly or indirectly.
        This is the forward dependency closure.
        """
        relative_path = str(Path(file_path).relative_to(self.project_root))
        if relative_path not in self.graph:
            return set()

        # nx.descendants finds all nodes reachable from the given node.
        descendants = nx.descendants(self.graph, relative_path)
        return {self.project_root / p for p in descendants}

    def save(self, path: str | Path) -> None:
        """Saves the graph to a file."""
        nx.write_gml(self.graph, str(path))

    @classmethod
    def load(cls, path: str | Path, project_root: str | Path) -> 'DependencyGraph':
        """Loads the graph from a file."""
        instance = cls(project_root)
        instance.graph = nx.read_gml(path)
        return instance
