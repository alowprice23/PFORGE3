import pytest
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.orchestrator.state_bus import PuzzleState

# A set of default constants for testing
TEST_CONSTANTS = {
    "w_issues": 0.6,
    "w_tests": 0.4,
    "w_entropy": 0.2,
    "w_risk": 0.1,
    "w_backtracks": 0.1,
    "w_phi": 2.0,
}

def test_efficiency_engine_initial_state():
    """
    Tests that the efficiency of a default, empty state is calculated correctly.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState()

    # In a default state, progress is 100% and penalties are 0
    # So the score should be the sum of the progress weights
    expected_score = TEST_CONSTANTS["w_issues"] * 1.0 + TEST_CONSTANTS["w_tests"] * 1.0

    assert engine.compute(state) == pytest.approx(expected_score)

def test_efficiency_with_issues():
    """
    Tests that efficiency decreases as the number of open issues increases.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(total_issues=10, closed_issues=5)

    progress_issues = 5 / 10
    expected_score = (TEST_CONSTANTS["w_issues"] * progress_issues) + (TEST_CONSTANTS["w_tests"] * 1.0)

    assert engine.compute(state) == pytest.approx(expected_score)

def test_efficiency_with_penalties():
    """
    Tests that penalties like entropy, risk, and backtracks decrease the score.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(
        tick=10,
        entropy=0.5,
        risk=20,
        backtracks=5
    )

    # Start with perfect progress
    base_score = TEST_CONSTANTS["w_issues"] + TEST_CONSTANTS["w_tests"]

    # Subtract penalties
    penalty = (
        TEST_CONSTANTS["w_entropy"] * 0.5 +
        TEST_CONSTANTS["w_risk"] * (20 / 10) +
        TEST_CONSTANTS["w_backtracks"] * (5 / 10)
    )

    expected_score = base_score - penalty

    assert engine.compute(state) == pytest.approx(expected_score)

def test_efficiency_with_phi_reward():
    """
    Tests that removing false pieces (phi) increases the score.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(
        tick=10,
        phi=2
    )

    base_score = TEST_CONSTANTS["w_issues"] + TEST_CONSTANTS["w_tests"]
    reward = TEST_CONSTANTS["w_phi"] * (2 / 10)
    expected_score = base_score + reward

    assert engine.compute(state) == pytest.approx(expected_score)

def test_efficiency_score_is_not_negative():
    """
    Ensures the efficiency score is always clamped at 0 and never goes negative.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    # A state with very high penalties
    state = PuzzleState(tick=1, entropy=100, risk=100)

    assert engine.compute(state) == 0.0
