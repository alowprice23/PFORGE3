from __future__ import annotations
import libcst as cst
from libcst.tool import suite
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor, RemoveImportsVisitor, GatherImportsVisitor

def reorder_imports(code: str) -> str:
    """
    Sorts imports according to a standard style (e.g., isort).
    This is a simplified implementation that sorts alphabetically.
    """
    tree = cst.parse_module(code)
    gatherer = GatherImportsVisitor(CodemodContext())
    tree.visit(gatherer)

    sorted_imports = sorted(gatherer.all_imports, key=lambda i: i.module.value)

    # Remove all original imports
    tree_no_imports = tree.visit(RemoveImportsVisitor(CodemodContext(), gatherer.all_imports))

    # Add them back in sorted order
    context = CodemodContext()
    AddImportsVisitor.add_needed_import(context, "typing", "List") # Example
    for imp in sorted_imports:
         AddImportsVisitor.add_needed_import(context, imp.module.value, imp.name.value if hasattr(imp, 'name') else None)


    tree_with_sorted_imports = tree_no_imports.visit(AddImportsVisitor(context))
    return tree_with_sorted_imports.code


def remove_unused_imports(code: str) -> str:
    """
    Removes import statements that are not referenced in the code.
    This uses the built-in LibCST transformer.
    """
    context = CodemodContext()
    command = suite.load_codemod(
        "RemoveUnusedImportsCommand", context, "libcst.codemod"
    )
    tree = cst.parse_module(code)
    updated_tree = command.transform_module(tree)
    return updated_tree.code


class LocalizeImportTransformer(cst.CSTTransformer):
    """
    A transformer to move a top-level import into a function.
    """
    def __init__(self, import_name: str, function_name: str):
        self.import_name = import_name
        self.function_name = function_name
        self.import_to_move: cst.Import | cst.ImportFrom | None = None

    def visit_Import_or_ImportFrom(self, node: cst.Import | cst.ImportFrom) -> bool:
        # Find the import to move
        for alias in node.names:
            if alias.name.value == self.import_name:
                self.import_to_move = node
                return False  # Stop searching
        return True

    def leave_Import_or_ImportFrom(
        self, original_node: cst.Import | cst.ImportFrom, updated_node: cst.Import | cst.ImportFrom
    ) -> cst.Import | cst.ImportFrom | cst.RemovalSentinel:
        # Remove the import from the top level
        if updated_node is self.import_to_move:
            return cst.RemoveFromParent()
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Insert the import at the beginning of the target function
        if updated_node.name.value == self.function_name and self.import_to_move:
            new_body = [self.import_to_move] + list(updated_node.body.body)
            return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))
        return updated_node


def localize_import(code: str, import_name: str, function_name: str) -> str:
    """
    Moves an import statement from the module level to the local scope of a
    function to break an import cycle.
    """
    tree = cst.parse_module(code)
    transformer = LocalizeImportTransformer(import_name, function_name)
    updated_tree = tree.visit(transformer)
    return updated_tree.code
