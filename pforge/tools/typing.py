from __future__ import annotations
import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor

class AddTypeStubTransformer(cst.CSTTransformer):
    """
    A transformer to add 'Any' type stubs to functions without annotations.
    """
    def __init__(self, context: CodemodContext):
        self.context = context

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Check if there is already a return annotation.
        if updated_node.returns:
            return updated_node

        # Add '-> Any' as the return annotation.
        AddImportsVisitor.add_needed_import(self.context, "typing", "Any")
        return updated_node.with_changes(
            returns=cst.Annotation(annotation=cst.Name("Any"))
        )


def add_type_stub(code: str) -> str:
    """
    Adds a basic '-> Any' type stub to functions that are missing one.
    """
    tree = cst.parse_module(code)
    context = CodemodContext()
    transformer = AddTypeStubTransformer(context)
    updated_tree = tree.visit(transformer)

    # Add the 'from typing import Any' import if it was needed.
    importer = AddImportsVisitor(context)
    final_tree = updated_tree.visit(importer)
    return final_tree.code


class NarrowCastTransformer(cst.CSTTransformer):
    """
    A transformer to wrap a variable in a typing.cast call.
    """

    def __init__(self, context: CodemodContext, variable_name: str, new_type: str):
        self.context = context
        self.variable_name = variable_name
        self.new_type = new_type

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        # This is a simplification. A real implementation would need to
        # understand scope to avoid casting variables with the same name
        # in different scopes.
        if updated_node.value == self.variable_name:
            AddImportsVisitor.add_needed_import(self.context, "typing", "cast")
            return cst.Call(
                func=cst.Name("cast"),
                args=[
                    cst.Arg(value=cst.Name(self.new_type)),
                    cst.Arg(value=updated_node),
                ],
            )
        return updated_node


def add_narrow_cast(code: str, variable_name: str, new_type: str) -> str:
    """
    Inserts a 'typing.cast' call to narrow the type of a variable.

    Args:
        code: The source code to transform.
        variable_name: The name of the variable to cast.
        new_type: The name of the type to cast to (as a string).
    """
    tree = cst.parse_module(code)
    context = CodemodContext()
    transformer = NarrowCastTransformer(context, variable_name, new_type)
    updated_tree = tree.visit(transformer)

    # Add the 'from typing import cast' import if it was needed.
    importer = AddImportsVisitor(context)
    final_tree = updated_tree.visit(importer)
    return final_tree.code
