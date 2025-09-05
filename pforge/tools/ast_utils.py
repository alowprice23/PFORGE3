from __future__ import annotations
import functools
from typing import Type, Callable, List, Dict, Any

import libcst as cst
from libcst.metadata import PositionProvider, CodeRange
from zss import simple_distance, Node as ZssNode

# A unique object to use as a marker in metadata.
_EDITED_MARKER = object()


class _ImportVisitor(cst.CSTVisitor):
    """
    A LibCST visitor that finds disallowed imports in a module.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, disallowed_imports: List[str]):
        self.disallowed_imports = set(disallowed_imports)
        self.violations: List[Dict[str, Any]] = []

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if alias.name.value in self.disallowed_imports:
                pos = self.get_metadata(PositionProvider, node)
                self.violations.append({
                    "type": "direct_import",
                    "import": alias.name.value,
                    "line": pos.start.line,
                })

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            return

        module_name = node.module.value
        pos = self.get_metadata(PositionProvider, node)
        # Case 1: The 'from' part is disallowed, e.g., `from pforge.server import ...`
        if module_name in self.disallowed_imports:
            self.violations.append({
                "type": "from_import",
                "import": module_name,
                "line": pos.start.line,
            })
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
                self.violations.append({
                    "type": "sub_import",
                    "import": full_import_path,
                    "line": pos.start.line,
                })


def find_disallowed_imports(tree: cst.CSTNode, disallowed_list: List[str]) -> List[Dict[str, Any]]:
    """
    Parses a LibCST tree and returns a list of disallowed import violations.
    """
    visitor = _ImportVisitor(disallowed_imports=disallowed_list)
    wrapper = cst.MetadataWrapper(tree)
    wrapper.visit(visitor)
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


class _SymbolCollector(cst.CSTVisitor):
    """
    A visitor to collect all function and class definitions from a CST.
    """
    def __init__(self):
        self.symbols = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.symbols[node.name.value] = node

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.symbols[node.name.value] = node


def find_modified_symbols(code1: str, code2: str) -> set[str]:
    """
    Compares two Python source code strings and returns the names of functions
    and classes that were added, removed, or changed.
    """
    try:
        tree1 = cst.parse_module(code1)
        tree2 = cst.parse_module(code2)
    except cst.ParserSyntaxError:
        # If there's a syntax error, we can't reliably compare.
        # A safe fallback is to assume the whole file is modified.
        return {"<file>"}

    collector1 = _SymbolCollector()
    collector2 = _SymbolCollector()
    tree1.visit(collector1)
    tree2.visit(collector2)

    symbols1 = collector1.symbols
    symbols2 = collector2.symbols

    modified_symbols = set()

    # Find added and changed symbols
    for name, node2 in symbols2.items():
        if name not in symbols1:
            modified_symbols.add(name)
        else:
            node1 = symbols1[name]
            # .deep_equals() is a reliable way to check for semantic identity
            if not node1.deep_equals(node2):
                modified_symbols.add(name)

    # Find removed symbols
    for name in symbols1:
        if name not in symbols2:
            modified_symbols.add(name)

    return modified_symbols
