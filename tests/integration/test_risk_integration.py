import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from pforge.agents.predictor_agent import PredictorAgent
from pforge.agents.planner_agent import PlannerAgent
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message, MsgType
from pforge.project import Project
from pforge.storage.risk_model_db import RiskModelDB
from pforge.validation.coverage_index import CoverageIndex

from types import SimpleNamespace

@pytest.fixture
def mock_config():
    """Provides a mock config object."""
    class MockConfig:
        def __init__(self):
            self.llm = SimpleNamespace(**{"model": "gpt-4-turbo"})
            self.doctor = SimpleNamespace(**{"retry_limit": 3})
            self.specifications = SimpleNamespace(**{"raw_config": {}})
            self.recovery = SimpleNamespace(**{"enabled": False, "checks": []})
            self.budget = SimpleNamespace(**{"tenant": "test-tenant", "daily_quota_tokens": 1000})
            self.planner = SimpleNamespace(**{"effort_budget_per_tick": 30.0})

    return MockConfig()

@pytest.fixture
def mock_project(tmp_path):
    """Provides a mock project."""
    (tmp_path / "pforge").mkdir()
    (tmp_path / "pforge" / "some_feature.py").write_text("def some_function(): return True")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "unit").mkdir()
    (tests_dir / "unit" / "test_some_feature.py").write_text(
        "from pforge.some_feature import some_function\n\n"
        "def test_case():\n"
        "    assert some_function() is True\n"
    )
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
    risk_db = RiskModelDB()
    coverage_index = CoverageIndex(project_root=mock_project.root)
    coverage_index.load()
    predictor = PredictorAgent(
        bus, mock_config, mock_project, risk_db=risk_db, coverage_index=coverage_index
    )

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

    # 4. Capture the first analysis and its risk score
    first_analysis_msg = await bus.get("test_listener", timeout=1)
    assert first_analysis_msg is not None
    initial_risk_score = first_analysis_msg.payload['risk_score']

    # === Part 2: Simulate a failed fix and re-assess risk ===

    # 5. Simulate two failed patches for the same file
    fix_failed_payload = {"file_path": test_file, "op_id": "dummy_op_1"}
    await bus.publish(MsgType.FIX_PATCH_REJECTED.value, Message(type=MsgType.FIX_PATCH_REJECTED, payload=fix_failed_payload))
    await predictor.on_tick()

    fix_failed_payload_2 = {"file_path": test_file, "op_id": "dummy_op_2"}
    await bus.publish(MsgType.FIX_PATCH_REJECTED.value, Message(type=MsgType.FIX_PATCH_REJECTED, payload=fix_failed_payload_2))
    await predictor.on_tick()

    # 6. Publish the same failure again
    await bus.publish(MsgType.TESTS_FAILED.value, test_failure_msg)
    # We don't need to re-initialize the agent, just run its tick again.
    await predictor.on_tick()

    # 7. Capture the second analysis
    second_analysis_msg = await bus.get("test_listener", timeout=1)
    assert second_analysis_msg is not None
    updated_risk_score = second_analysis_msg.payload['risk_score']

    # 8. Assert that the risk score is now higher due to learned risk
    assert updated_risk_score > initial_risk_score

    # === Part 3: Ensure Planner still works (light check) ===
    state_bus = MagicMock()
    planner = PlannerAgent(bus, mock_config, mock_project, state_bus=state_bus)
    await bus.publish(MsgType.TASK_ANALYZED.value, second_analysis_msg)
    await planner.on_tick()
    assert len(planner.task_board) == 1

    predictor.risk_db.close()
