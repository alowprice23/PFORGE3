from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pforge.orchestrator.signals import Message, MsgType
from pforge.proof.capabilities import issue_token
from tests.helpers import ConcreteTestAgent

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
async def test_receive_and_verify_general_capability(test_agent):
    op_id = "test_op_123"
    test_agent.bus.redis_client.sadd.return_value = 1
    token = issue_token(actor="test_agent", scope=["exec:test"], op_id=op_id, expires_in_seconds=10)
    test_agent.receive_token(token, op_id)

    # Assert the agent has the general capability
    assert await test_agent.has_capability("exec:test", op_id) is True
    # A general capability should also grant a targeted request
    assert await test_agent.has_capability("exec:test", op_id, target="some/target") is True
    # Assert it does not have a different capability
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

    # --- Fourth check for a targeted permission when only general is granted ---
    assert await test_agent.has_capability("fs:read", op_id, target="/path/to/file") is True
    verify_mock.assert_called_once()

@pytest.mark.asyncio
async def test_publish_redacts_payload(test_agent, mock_bus):
    # This secret matches a pattern in policies/redaction/patterns.yaml
    secret_api_key = "password = 'my_super_secret_password_123'"

    # We will patch the scrub method of the global redaction_manager
    with patch('pforge.agents.base_agent.scrub') as mock_scrub:
        # Configure the mock to return a value that indicates redaction
        redacted_payload = {"log_message": "Some log with a secret: [REDACTED]"}
        mock_report = MagicMock()
        mock_report.total_redactions = 1
        mock_scrub.return_value = (redacted_payload, mock_report)

        message_with_secret = Message(
            type=MsgType.OBS_TICK,
            payload={"log_message": f"Some log with a secret: {secret_api_key}"}
        )

        await test_agent.publish(MsgType.OBS_TICK.value, message_with_secret)

        # Check what was actually published on the bus
        published_message = mock_bus.publish.call_args[0][1]

        # Assert that scrub was called with the original payload
        mock_scrub.assert_called_once_with(message_with_secret.payload)

        # Assert the payload of the published message is the scrubbed one
        assert published_message.payload == redacted_payload


@pytest.mark.asyncio
async def test_action_denied_without_capability(test_agent):
    """
    Tests that an agent is denied from performing an action if it does
    not have the required capability for the given op_id.
    """
    op_id = "test_op_789"
    # Note: We are NOT issuing or receiving a token for this op_id.

    assert await test_agent.has_capability("fs:write", op_id) is False
    assert await test_agent.has_capability("fs:write", op_id, target="/a/b") is False

@pytest.mark.asyncio
async def test_general_action_allowed_with_correct_capability(test_agent):
    """
    Tests that an agent is allowed to perform a general action if it has the
    correct capability.
    """
    op_id = "test_op_101"
    token = issue_token(actor="test_agent", scope=["exec:test"], op_id=op_id)
    test_agent.receive_token(token, op_id)
    test_agent.bus.redis_client.sadd.return_value = 1

    assert await test_agent.has_capability("exec:test", op_id) is True
    # A general capability should also grant a targeted request
    assert await test_agent.has_capability("exec:test", op_id, target="some/target") is True


@pytest.mark.asyncio
async def test_action_denied_with_wrong_general_capability(test_agent):
    """
    Tests that an agent is denied if it has a token for the op_id, but
    that token does not contain the required general permission.
    """
    op_id = "test_op_112"
    token = issue_token(actor="test_agent", scope=["fs:read"], op_id=op_id)
    test_agent.receive_token(token, op_id)
    test_agent.bus.redis_client.sadd.return_value = 1

    assert await test_agent.has_capability("fs:write", op_id) is False
