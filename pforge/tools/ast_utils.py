from __future__ import annotations
import functools
from typing import Type, Callable, List

import libcst as cst
from zss import simple_distance, Node as ZssNode

# A unique object to use as a marker in metadata.
_EDITED_MARKER = object()


class _ImportVisitor(cst.CSTVisitor):
    """
    A LibCST visitor that finds disallowed imports in a module.
    """
    def __init__(self, disallowed_imports: List[str]):
        self.disallowed_imports = set(disallowed_imports)
        self.violations: List[str] = []

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if alias.name.value in self.disallowed_imports:
                self.violations.append(f"Disallowed direct import of '{alias.name.value}'")

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            return

        module_name = node.module.value
        # Case 1: The 'from' part is disallowed, e.g., `from pforge.server import ...`
        if module_name in self.disallowed_imports:
            self.violations.append(f"Disallowed import from '{module_name}'")
            return # No need to check sub-imports if the whole module is banned

        # Case 2: A sub-module is disallowed, e.g., `from pforge import server`
        # where `pforge.server` is the disallowed module.
        if isinstance(node.names, cst.ImportStar):
            # We can't resolve wildcard imports statically here, but we could
            # flag them as risky if needed. For now, we ignore them.
            return

        for alias in node.names:
            # Reconstruct the full imported path
            full_import_path = f"{module_name}.{alias.name.value}"
            if full_import_path in self.disallowed_imports:
                self.violations.append(f"Disallowed import of '{full_import_path}'")


def find_disallowed_imports(tree: cst.CSTNode, disallowed_list: List[str]) -> List[str]:
    """
    Parses a LibCST tree and returns a list of disallowed import violations.
    """
    visitor = _ImportVisitor(disallowed_imports=disallowed_list)
    tree.visit(visitor)
    return visitor.violations

class _CstNodeAdapter(ZssNode):
    """
    An adapter to make LibCST nodes compatible with the zss library.
    """
    def __init__(self, cst_node: cst.CSTNode):
        self.cst_node = cst_node
        super().__init__(label=cst_node.__class__.__name__)

    @staticmethod
    def get_children(node: _CstNodeAdapter) -> list[_CstNodeAdapter]:
        """
        Returns a list of children of the given node.
        """
        children = []
        if isinstance(node.cst_node, cst.CSTNode):
            for child in node.cst_node.children:
                children.append(_CstNodeAdapter(child))
        return children

    @staticmethod
    def get_label(node: _CstNodeAdapter) -> str:
        """
        Returns the label of the given node.
        """
        return node.label


def idempotent_edit(transformer: Type[cst.CSTTransformer]) -> Callable:
    """
    A decorator that makes a LibCST transformer idempotent.

    It works by adding a marker to the metadata of each node that is
    transformed. On subsequent runs, it will not re-apply the transformation
    to nodes that already have the marker.
    """
    @functools.wraps(transformer)
    def wrapper(*args, **kwargs) -> cst.CSTTransformer:
        original_transformer = transformer(*args, **kwargs)

        class IdempotentTransformer(cst.CSTTransformer):
            def on_leave(
                self, original_node: cst.CSTNode, updated_node: cst.CSTNode
            ) -> cst.CSTNode:
                # Check if the marker is present.
                if self.get_metadata(_EDITED_MARKER, original_node, default=False):
                    return updated_node

                # Apply the original transformation.
                new_node = original_transformer.on_leave(original_node, updated_node)

                # If the node was changed, add the marker.
                if new_node is not original_node:
                    self.set_metadata(new_node, _EDITED_MARKER, True)

                return new_node

        return IdempotentTransformer()

    return wrapper


def edit_distance(tree1: cst.CSTNode, tree2: cst.CSTNode) -> int:
    """
    A function to calculate the edit distance between two ASTs.

    This uses the Zhang-Shasha algorithm implemented in the `zss` library.
    It provides a measure of the effort required to transform one tree into
    another.

    Args:
        tree1: The first LibCST tree.
        tree2: The second LibCST tree.

    Returns:
        The edit distance between the two trees.
    """
    # Adapt the LibCST trees to be compatible with the zss library.
    node1 = _CstNodeAdapter(tree1)
    node2 = _CstNodeAdapter(tree2)

    # Calculate the tree edit distance.
    # The result is cast to an int, as simple_distance returns a float.
    distance = simple_distance(
        node1,
        node2,
        get_children=_CstNodeAdapter.get_children,
        get_label=_CstNodeAdapter.get_label,
    )
    return int(distance)
