from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import Message, MsgType
from pforge.proof.capabilities import issue_token


# A concrete agent class for testing purposes
class ConcreteTestAgent(BaseAgent):
    name = "test_agent"
    async def on_tick(self):
        pass

@pytest.fixture
def mock_bus():
    bus = MagicMock()
    bus.redis_client = MagicMock()
    # This mock needs to be awaitable
    bus.redis_client.sadd = AsyncMock()
    bus.redis_client.expire = AsyncMock()
    bus.publish = AsyncMock()
    return bus

@pytest.fixture
def test_agent(mock_bus):
    config = MagicMock()
    project = MagicMock()
    return ConcreteTestAgent(bus=mock_bus, config=config, project=project)

import re


@pytest.mark.asyncio
async def test_receive_and_verify_capability(test_agent):
    op_id = "test_op_123"
    # The first call to sadd for a new nonce should return 1
    test_agent.bus.redis_client.sadd.return_value = 1

    # Issue a token with fs:write permission
    token = issue_token(actor="test_agent", scope=["fs:write"], op_id=op_id, expires_in_seconds=10)

    # Agent receives the token
    test_agent.receive_token(token, op_id)

    # Assert the agent now has the capability
    assert await test_agent.has_capability("fs:write", op_id) is True

    # Assert the agent does not have a different capability
    test_agent.bus.redis_client.sadd.return_value = 1 # reset mock for next check
    assert await test_agent.has_capability("fs:delete", op_id) is False

@pytest.mark.asyncio
async def test_capability_is_cached_after_first_verification(test_agent):
    """
    Tests that after a token is verified once, its payload is cached
    and subsequent capability checks for the same op_id do not trigger
    another verification (which would fail a replay check).
    """
    op_id = "test_op_456"
    token = issue_token(actor="test_agent", scope=["exec:test", "fs:read"], op_id=op_id, expires_in_seconds=10)
    test_agent.receive_token(token, op_id)

    # --- Mock the verification call (via redis) ---
    # We will track the calls to this mock.
    verify_mock = test_agent.bus.redis_client.sadd
    verify_mock.return_value = 1 # Simulate a successful, first-time verification

    # --- First check ---
    # This should trigger the actual verification.
    assert await test_agent.has_capability("exec:test", op_id) is True
    verify_mock.assert_called_once()

    # --- Second check for a different permission on the same token ---
    # This should use the cached payload and NOT trigger another verification.
    assert await test_agent.has_capability("fs:read", op_id) is True
    verify_mock.assert_called_once() # Assert that the mock was NOT called again

    # --- Third check for a permission that is not in the scope ---
    # This should also use the cache and fail without triggering verification.
    assert await test_agent.has_capability("fs:write", op_id) is False
    verify_mock.assert_called_once() # Assert that the mock was STILL not called again

@pytest.mark.asyncio
async def test_publish_redacts_payload(test_agent, mock_bus):
    # This secret matches a pattern in policies/redaction/patterns.yaml
    secret_api_key = "password = 'my_super_secret_password_123'"

    # We will patch the COMPILED_REDACTION_PATTERNS to avoid file loading issues in tests
    with patch('pforge.proof.redaction.COMPILED_REDACTION_PATTERNS', {
        "password_test": re.compile(r"(password\s*[:=]\s*['\"].*['\"])", re.IGNORECASE)
    }):
        message_with_secret = Message(
            type=MsgType.OBS_TICK,
            payload={"log_message": f"Some log with a secret: {secret_api_key}"}
        )

        await test_agent.publish(MsgType.OBS_TICK.value, message_with_secret)

        # Check what was actually published on the bus
        published_message = mock_bus.publish.call_args[0][1]

        # Assert the secret is gone and replaced with the placeholder
        assert secret_api_key not in published_message.payload["log_message"]
        assert "[REDACTED]" in published_message.payload["log_message"]
