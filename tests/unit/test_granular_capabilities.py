import pytest
from unittest.mock import MagicMock, AsyncMock

from pforge.proof.capabilities import issue_token
from tests.helpers import ConcreteTestAgent

@pytest.fixture
def mock_bus():
    bus = MagicMock()
    bus.redis_client = MagicMock()
    bus.redis_client.sadd = AsyncMock(return_value=1)
    bus.redis_client.expire = AsyncMock()
    return bus

@pytest.fixture
def test_agent(mock_bus):
    config = MagicMock()
    project = MagicMock()
    return ConcreteTestAgent(bus=mock_bus, config=config, project=project)

@pytest.mark.asyncio
async def test_granular_fs_write_permission_granted(test_agent):
    """Tests that a capability for a specific file path is correctly granted."""
    op_id = "granular_op_1"
    file_path = "/app/src/main.py"
    token = issue_token(actor=test_agent.name, scope=[f"fs:write:{file_path}"], op_id=op_id)
    test_agent.receive_token(token, op_id)

    assert await test_agent.has_capability("fs:write", op_id, target=file_path) is True

@pytest.mark.asyncio
async def test_granular_fs_write_permission_denied_for_different_path(test_agent):
    """Tests that a capability for a specific file path is denied for another path."""
    op_id = "granular_op_2"
    file_path_allowed = "/app/src/main.py"
    file_path_denied = "/app/src/other.py"
    token = issue_token(actor=test_agent.name, scope=[f"fs:write:{file_path_allowed}"], op_id=op_id)
    test_agent.receive_token(token, op_id)

    assert await test_agent.has_capability("fs:write", op_id, target=file_path_denied) is False

@pytest.mark.asyncio
async def test_granular_permission_denied_for_different_action(test_agent):
    """Tests that a fs:write capability does not grant fs:read."""
    op_id = "granular_op_3"
    file_path = "/app/src/main.py"
    token = issue_token(actor=test_agent.name, scope=[f"fs:write:{file_path}"], op_id=op_id)
    test_agent.receive_token(token, op_id)

    assert await test_agent.has_capability("fs:read", op_id, target=file_path) is False

@pytest.mark.asyncio
async def test_granular_permission_does_not_grant_general_permission(test_agent):
    """Tests that a capability for a specific file path does not grant the general permission."""
    op_id = "granular_op_4"
    file_path = "/app/src/main.py"
    token = issue_token(actor=test_agent.name, scope=[f"fs:write:{file_path}"], op_id=op_id)
    test_agent.receive_token(token, op_id)

    # The agent should not have a general "fs:write" capability
    assert await test_agent.has_capability("fs:write", op_id) is False

@pytest.mark.asyncio
async def test_general_permission_granted_alongside_granular(test_agent):
    """Tests that a general permission works correctly when a granular one is also present."""
    op_id = "granular_op_5"
    file_path = "/app/src/main.py"
    token = issue_token(actor=test_agent.name, scope=[f"fs:write:{file_path}", "exec:test"], op_id=op_id)
    test_agent.receive_token(token, op_id)

    assert await test_agent.has_capability("exec:test", op_id) is True
    # Make sure the granular permission still works
    assert await test_agent.has_capability("fs:write", op_id, target=file_path) is True
    # And that a general fs:write is still denied
    assert await test_agent.has_capability("fs:write", op_id) is False

@pytest.mark.asyncio
async def test_general_permission_works_standalone(test_agent):
    """Tests that a general permission works correctly by itself."""
    op_id = "granular_op_6"
    token = issue_token(actor=test_agent.name, scope=["exec:test"], op_id=op_id)
    test_agent.receive_token(token, op_id)

    assert await test_agent.has_capability("exec:test", op_id) is True
    assert await test_agent.has_capability("exec:test", op_id, target="/some/path") is True
