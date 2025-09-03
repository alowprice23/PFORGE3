import pytest
import numpy as np
from unittest.mock import patch

from pforge.agents.predictor_agent import PredictorAgent
from pforge.agents.planner_agent import PlannerAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message, MsgType
from pforge.config import Config, LLMConfig, DoctorConfig, SpecificationsConfig, RecoveryConfig
from pforge.project import Project
from pforge.storage.risk_model_db import RiskModelDB

@pytest.fixture
def mock_config():
    """Provides a default config."""
    return Config(
        llm=LLMConfig(model="gpt-4-turbo"),
        doctor=DoctorConfig(retry_limit=3),
        specifications=SpecificationsConfig(raw_config={}),
        recovery=RecoveryConfig(enabled=False, checks=[])
    )

@pytest.fixture
def mock_project(tmp_path):
    """Provides a mock project."""
    return Project(root_path=tmp_path)

@pytest.mark.asyncio
@patch('pforge.storage.risk_model_db.DB_PATH', ":memory:")
async def test_risk_model_updates_and_affects_planning(mock_config, mock_project):
    """
    Tests that the PredictorAgent updates its risk model in the DB and that
    this learned risk affects the effort distribution sent to the Planner.
    """
    bus = InMemoryBus()

    # === Part 1: Initial failure with default risk ===

    # 1. Initialize agents
    predictor = PredictorAgent(bus, mock_config, mock_project)

    # Subscribe to the predictor's output
    bus.subscribe("test_listener", MsgType.TASK_ANALYZED.value)

    # 2. Mock a test failure message
    test_file = "pforge/some_feature.py"
    failure_payload = {
        "failed_tests": [{"nodeid": f"tests/unit/test_{test_file.split('/')[-1]}::test_case"}]
    }
    test_failure_msg = Message(type=MsgType.TESTS_FAILED, payload=failure_payload)

    # 3. Publish the failure and run the predictor
    await bus.publish(MsgType.TESTS_FAILED.value, test_failure_msg)
    await predictor.on_tick()

    # 4. Capture the first analysis and its effort mean
    first_analysis_msg = await bus.get("test_listener", timeout=1)
    assert first_analysis_msg is not None
    initial_effort_dist = first_analysis_msg.payload['effort_distribution']
    initial_mean_effort = np.mean(initial_effort_dist)

    # === Part 2: Simulate a failed fix and re-assess risk ===

    # 5. Manually update the risk model to simulate a failed patch for that file
    predictor.risk_db.update_risk_params(test_file, success=False)
    predictor.risk_db.update_risk_params(test_file, success=False)

    # 6. Publish the same failure again
    await bus.publish(MsgType.TESTS_FAILED.value, test_failure_msg)
    await predictor.on_tick()

    # 7. Capture the second analysis
    second_analysis_msg = await bus.get("test_listener", timeout=1)
    assert second_analysis_msg is not None
    updated_effort_dist = second_analysis_msg.payload['effort_distribution']
    updated_mean_effort = np.mean(updated_effort_dist)

    # 8. Assert that the mean effort is now higher due to learned risk
    assert updated_mean_effort > initial_mean_effort

    # === Part 3: Ensure Planner still works (light check) ===
    planner = PlannerAgent(bus, mock_config, mock_project)
    await bus.publish(MsgType.TASK_ANALYZED.value, second_analysis_msg)
    await planner.on_tick()
    assert len(planner.task_board) == 1

    predictor.risk_db.close()
