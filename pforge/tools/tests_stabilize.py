from __future__ import annotations
import libcst as cst

class InjectFixtureTransformer(cst.CSTTransformer):
    """
    A transformer to inject a fixture into test function arguments.
    """

    def __init__(self, fixture_name: str):
        self.fixture_name = fixture_name

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Only modify functions that look like tests.
        if not original_node.name.value.startswith("test_"):
            return updated_node

        # Check if the fixture is already present.
        for param in original_node.params.params:
            if param.name.value == self.fixture_name:
                return updated_node

        # Add the new fixture to the parameter list.
        new_param = cst.Param(name=cst.Name(self.fixture_name))
        new_params = list(updated_node.params.params) + [new_param]
        return updated_node.with_changes(
            params=updated_node.params.with_changes(params=tuple(new_params))
        )


def inject_clock_fixture(code: str) -> str:
    """
    Injects a 'clock' fixture into all test functions.
    """
    tree = cst.parse_module(code)
    transformer = InjectFixtureTransformer("clock")
    updated_tree = tree.visit(transformer)
    return updated_tree.code


def inject_rng_fixture(code: str) -> str:
    """
    Injects a 'seeded_rng' fixture into all test functions.
    """
    tree = cst.parse_module(code)
    transformer = InjectFixtureTransformer("seeded_rng")
    updated_tree = tree.visit(transformer)
    return updated_tree.code


class SwapFixtureTransformer(cst.CSTTransformer):
    """
    A transformer to swap one fixture for another in test functions.
    """

    def __init__(self, old_fixture: str, new_fixture: str):
        self.old_fixture = old_fixture
        self.new_fixture = new_fixture

    def leave_Param(
        self, original_node: cst.Param, updated_node: cst.Param
    ) -> cst.Param:
        if original_node.name.value == self.old_fixture:
            return updated_node.with_changes(name=cst.Name(self.new_fixture))
        return updated_node


def swap_network_fixture(code: str, old: str = "live_server", new: str = "mock_server") -> str:
    """
    Swaps a live network fixture with a mock one in all test functions.
    """
    tree = cst.parse_module(code)
    transformer = SwapFixtureTransformer(old, new)
    updated_tree = tree.visit(transformer)
    return updated_tree.code
