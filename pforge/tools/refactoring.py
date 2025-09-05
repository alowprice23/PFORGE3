from __future__ import annotations
import libcst as cst
from libcst.metadata import (
    PositionProvider,
    ParentNodeProvider,
    ScopeProvider,
    ExpressionContextProvider,
    ExpressionContext,
)
from libcst.metadata.scope_provider import Assignment, ClassScope
from typing import List, Set


import builtins

class _ParameterFinder(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (ExpressionContextProvider,)

    def __init__(self):
        self.defined_vars: Set[str] = set()
        self.used_vars: Set[str] = set()

    def visit_Name(self, node: cst.Name) -> None:
        if node.value == "self" or node.value in dir(builtins):
            return

        context = self.get_metadata(ExpressionContextProvider, node)
        if context == ExpressionContext.STORE:
            self.defined_vars.add(node.value)
        elif context == ExpressionContext.LOAD:
            if node.value not in self.defined_vars:
                self.used_vars.add(node.value)

def get_parameters(nodes: List[cst.BaseStatement]) -> List[str]:
    finder = _ParameterFinder()
    wrapper = cst.MetadataWrapper(cst.Module(body=nodes))
    wrapper.visit(finder)
    return sorted(list(finder.used_vars))


class ExtractMethodTransformer(cst.CSTTransformer):
    """
    A transformer to extract a block of statements into a new method.
    """
    METADATA_DEPENDENCIES = (ParentNodeProvider, PositionProvider, ScopeProvider)

    def __init__(self, start_line: int, end_line: int, new_method_name: str):
        self.start_line = start_line
        self.end_line = end_line
        self.new_method_name = new_method_name
        self.extracted_method: cst.FunctionDef | None = None
        self.extraction_parent: cst.CSTNode | None = None

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.BaseSuite | cst.FlattenSentinel[cst.BaseStatement]:
        if self.extracted_method:
            return updated_node

        new_body = []
        nodes_to_extract = []
        is_extracting = False
        extraction_done = False

        for i, stmt in enumerate(original_node.body):
            pos = self.get_metadata(PositionProvider, stmt)
            if pos.start.line >= self.start_line and not extraction_done:
                is_extracting = True

            if is_extracting:
                nodes_to_extract.append(updated_node.body[i])
                if pos.end.line >= self.end_line:
                    is_extracting = False
                    extraction_done = True
                    scope = self.get_metadata(ScopeProvider, original_node)
                    parent_is_class = isinstance(scope.parent, ClassScope)
                    self._create_method_and_call(nodes_to_extract, new_body, parent_is_class)
            else:
                new_body.append(updated_node.body[i])

        if nodes_to_extract:
            self.extraction_parent = self.get_metadata(ParentNodeProvider, original_node)
            return updated_node.with_changes(body=new_body)
        return updated_node

    def _create_method_and_call(self, nodes: List[cst.BaseStatement], body: List[cst.BaseStatement], parent_is_class: bool):
        params = get_parameters(nodes)

        # Create the new method
        new_method_params_list = [cst.Param(name=cst.Name(p)) for p in params]
        if parent_is_class:
            new_method_params_list.insert(0, cst.Param(name=cst.Name("self")))

        new_method_params = cst.Parameters(
            params=new_method_params_list
        )
        self.extracted_method = cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=new_method_params,
            body=cst.IndentedBlock(body=nodes),
        )

        # Create the call to the new method
        if parent_is_class:
            # Note: This is a simplification. We should properly detect if we are in a class.
            # For now, let's assume if we are in a method, we need `self`.
            func_expr = cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.new_method_name))
        else:
            func_expr = cst.Name(self.new_method_name)

        call = cst.Call(
            func=func_expr,
            args=[cst.Arg(value=cst.Name(p)) for p in params],
        )
        body.append(cst.Expr(value=call))

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        if self.extracted_method:
            return updated_node.with_changes(
                body=[*updated_node.body, self.extracted_method]
            )
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if self.extracted_method and self.extraction_parent is original_node:
            return updated_node.with_changes(
                body=updated_node.body.with_changes(
                    body=[*updated_node.body.body, self.extracted_method]
                )
            )
        return updated_node


def extract_method(code: str, start_line: int, end_line: int, new_method_name: str) -> str:
    """
    Extracts a block of code into a new method.

    Args:
        code: The source code to refactor.
        start_line: The starting line of the code block to extract.
        end_line: The ending line of the code block.
        new_method_name: The name of the new method to create.

    Returns:
        The refactored code.
    """
    tree = cst.parse_module(code)
    wrapper = cst.MetadataWrapper(tree)
    transformer = ExtractMethodTransformer(start_line, end_line, new_method_name)

    modified_tree = wrapper.visit(transformer)

    return modified_tree.code


class _FindNameNodeVisitor(cst.CSTVisitor):
    """
    A visitor to find the Name node at a specific line and column.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, line: int, col: int):
        self.line = line
        self.col = col
        self.found_node: cst.Name | None = None

    def visit_Name(self, node: cst.Name) -> None:
        if self.found_node:
            return  # Already found, no need to traverse further

        pos = self.get_metadata(PositionProvider, node)
        if pos.start.line == self.line and pos.start.column <= self.col < pos.end.column:
            self.found_node = node


class _RenameSymbolTransformer(cst.CSTTransformer):
    """
    A transformer that renames a specific set of nodes.
    """
    def __init__(self, nodes_to_rename: Set[cst.CSTNode], new_name: str):
        self.nodes_to_rename = nodes_to_rename
        self.new_name = new_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if original_node in self.nodes_to_rename:
            return updated_node.with_changes(value=self.new_name)
        return updated_node


def rename_symbol(code: str, line: int, col: int, new_name: str) -> str:
    """
    Renames a symbol (variable, parameter, etc.) at a given location using
    scope-aware analysis.

    Args:
        code: The source code to refactor.
        line: The line number of the symbol to rename.
        col: The column number of the symbol to rename.
        new_name: The new name for the symbol.

    Returns:
        The refactored code, or the original code if the symbol was not found.
    """
    try:
        tree = cst.parse_module(code)
    except cst.ParserSyntaxError:
        return code

    wrapper = cst.MetadataWrapper(tree)

    finder = _FindNameNodeVisitor(line, col)
    wrapper.visit(finder)

    if not finder.found_node:
        return code

    scope_map = wrapper.resolve(ScopeProvider)
    scope = scope_map.get(finder.found_node)
    if not scope:
        return code

    assignments = scope[finder.found_node.value]
    nodes_to_rename = set()
    for assignment in assignments:
        if isinstance(assignment, Assignment):
            if isinstance(assignment.node, cst.Param):
                nodes_to_rename.add(assignment.node.name)
            elif isinstance(assignment.node, cst.FunctionDef):
                nodes_to_rename.add(assignment.node.name)
            else:
                nodes_to_rename.add(assignment.node)
        for access in assignment.references:
            nodes_to_rename.add(access.node)

    if not nodes_to_rename:
        return code

    transformer = _RenameSymbolTransformer(nodes_to_rename, new_name)
    modified_tree = wrapper.visit(transformer)
    return modified_tree.code
