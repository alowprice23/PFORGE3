from __future__ import annotations
import libcst as cst
from libcst.codemod import CodemodContext, transform_module, TransformSuccess, ContextAwareTransformer
from libcst.codemod.commands.remove_unused_imports import RemoveUnusedImportsCommand
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
    transformer = RemoveUnusedImportsCommand(CodemodContext())
    result = transform_module(transformer, code)
    if isinstance(result, TransformSuccess):
        return result.code
    else:
        # In case of errors, return the original code
        return code


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


class ImportDiscoveryVisitor(cst.CSTVisitor):
    """
    A visitor to find all imports of a specific symbol from a specific module.
    """
    def __init__(self, target_module_path: str, target_symbol: str):
        self.target_module_path = target_module_path
        self.target_symbol = target_symbol
        self.found_imports = []

    def visit_ImportFrom(self, node: cst.ImportFrom):
        # This is a simplified approach. A full implementation would need to
        # resolve the module path correctly (e.g., handle relative imports, packages, etc.)
        if node.module is None:
            return

        imported_module_str = cst.Module([node.module]).code

        if self.target_module_path == imported_module_str:
            if isinstance(node.names, cst.ImportStar):
                self.found_imports.append((node, "*"))
            else:
                for alias in node.names:
                    if alias.name.value == self.target_symbol:
                        self.found_imports.append((node, self.target_symbol))

def find_symbol_imports(project: 'Project', symbol: str, original_file_path: str) -> dict:
    """
    Finds all files in a project that import a specific symbol from a specific file.
    """
    search_results = {}

    target_module_path = original_file_path.replace('.py', '').replace('/', '.')

    for file_path in project.list_files("**/*.py"):
        if file_path == original_file_path:
            continue

        try:
            content = project.read_file(file_path)
            tree = cst.parse_module(content)
            visitor = ImportDiscoveryVisitor(target_module_path, symbol)
            tree.visit(visitor)

            if visitor.found_imports:
                search_results[file_path] = visitor.found_imports
        except Exception as e:
            print(f"Could not parse or analyze {file_path}: {e}")

    return search_results


class ImportRewriter(ContextAwareTransformer):
    """
    A transformer to rewrite an import statement.
    """
    def __init__(self, context: CodemodContext, symbol_to_move: str, old_module: str, new_module: str):
        super().__init__(context)
        self.symbol_to_move = symbol_to_move
        self.old_module = old_module
        self.new_module = new_module

    def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom) -> cst.ImportFrom | cst.RemovalSentinel:
        if original_node.module is None:
            return updated_node

        imported_module_str = cst.Module([original_node.module]).code
        if imported_module_str == self.old_module:
            if isinstance(original_node.names, cst.ImportStar):
                return updated_node

            names_to_keep = []
            found_symbol = False
            for alias in original_node.names:
                if alias.name.value == self.symbol_to_move:
                    found_symbol = True
                else:
                    names_to_keep.append(alias)

            if found_symbol:
                AddImportsVisitor.add_needed_import(self.context, self.new_module, self.symbol_to_move)

                if not names_to_keep:
                    return cst.RemoveFromParent()
                else:
                    return updated_node.with_changes(names=names_to_keep)

        return updated_node


def rewrite_imports(project: 'Project', symbol: str, old_path: str, new_path: str) -> list[str]:
    """
    Finds and rewrites all imports of a symbol in a project.
    Returns a list of modified file paths.
    """
    import_locations = find_symbol_imports(project, symbol, old_path)
    modified_files = []

    old_module = old_path.replace('.py', '').replace('/', '.')
    new_module = new_path.replace('.py', '').replace('/', '.')

    for file_path, _ in import_locations.items():
        try:
            content = project.read_file(file_path)
            tree = cst.parse_module(content)

            context = CodemodContext()
            transformer = ImportRewriter(context, symbol, old_module, new_module)

            modified_tree = tree.visit(transformer)

            add_imports_visitor = AddImportsVisitor(context)
            final_tree = modified_tree.visit(add_imports_visitor)

            project.write_file(file_path, final_tree.code)
            modified_files.append(file_path)
        except Exception as e:
            print(f"Could not rewrite imports in {file_path}: {e}")

    return modified_files
