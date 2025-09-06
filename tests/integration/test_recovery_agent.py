from unittest.mock import patch

import pytest

from pforge.agents.recovery_agent import RecoveryAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import MsgType
from pforge.project import Project


from pforge.config import RecoveryCheck, RecoveryConfig

@pytest.fixture
def mock_config():
    """Provides a mock config object."""
    class MockConfig:
        def __init__(self):
            self.llm = {"model": "gpt-4-turbo"}
            self.doctor = {"retry_limit": 3}
            self.specifications = {"raw_config": {}}
            self.recovery = RecoveryConfig(
                enabled=True,
                checks=[
                    RecoveryCheck(
                        detector="pforge.recovery.detectors.packages.check_pip_dependencies",
                        action="pforge.recovery.actions.pkg_resolve.install_packages"
                    )
                ]
            )
            self.budget = {"tenant": "test-tenant", "daily_quota_tokens": 1000}
            self.planner = {"effort_budget_per_tick": 30.0}
            self.agents = [
                {
                    "name": "recovery",
                    "startup_capabilities": ["system:load_dynamic_modules", "exec:recovery_action"]
                }
            ]
    return MockConfig()

@pytest.fixture
def mock_project(tmp_path):
    """Provides a mock project."""
    return Project(root_path=tmp_path)

@pytest.mark.asyncio
@patch('pforge.recovery.actions.pkg_resolve.install_packages')
@patch('pforge.recovery.detectors.packages.check_pip_dependencies')
async def test_recovery_agent_triggers_action_on_failure(
    mock_check_pip, mock_install_packages, mock_config, mock_project
):
    """
    Tests that the RecoveryAgent correctly calls an action when its
    corresponding detector reports a failure.
    """
    # 1. Arrange
    # Configure mocks to have a __name__ attribute for logging
    mock_check_pip.__name__ = "check_pip_dependencies"
    mock_install_packages.__name__ = "install_packages"

    # Mock the detector to report a failure
    mock_check_pip.return_value = (False, {"error": "dependency conflict"})
    # Mock the action to check if it's called
    mock_install_packages.return_value = {"status": "success"}

    bus = InMemoryBus()
    agent = RecoveryAgent(bus, mock_config, mock_project)
    agent.grant_startup_capabilities(mock_config.agents[0]["startup_capabilities"])


    # Subscribe to the agent's output message
    bus.subscribe("test_listener", MsgType.RECOVERY_ACTION_TAKEN.value)

    # 2. Act
    await agent.on_startup()
    await agent.on_tick()

    # 3. Assert
    # Check that the detector was called
    mock_check_pip.assert_called_once()

    # Check that the recovery action was called
    mock_install_packages.assert_called_once()

    # Check that a message was published to the bus
    recovery_msg = await bus.get("test_listener", timeout=1)
    assert recovery_msg is not None
    assert recovery_msg.type == MsgType.RECOVERY_ACTION_TAKEN
    assert recovery_msg.payload["action_name"] == "install_packages"
    assert recovery_msg.payload["failure_details"]["error"] == "dependency conflict"
