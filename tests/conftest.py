# tests/conftest.py
"""
This file contains shared fixtures for the tests.
"""

import pytest

@pytest.fixture
def dummy_fixture():
    """A dummy fixture."""
    return "dummy"
