from __future__ import annotations
import functools
from typing import Type, Callable, cast

import libcst as cst
from zss import simple_distance, Node as ZssNode

# A unique object to use as a marker in metadata.
_EDITED_MARKER = object()

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
