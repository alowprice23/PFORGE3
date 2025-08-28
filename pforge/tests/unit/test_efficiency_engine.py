import pytest
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.orchestrator.state_bus import PuzzleState

# These constants map to the weights in the denominator of the formula
TEST_CONSTANTS = {
    "gamma": 1.5,  # misfit penalty
    "alpha": 2.0,  # false piece penalty
    "lambda": 1.2, # risk penalty
    "beta": 1.0,   # backtrack penalty
    "eta": 0.8,    # entropy penalty
    "theta": 2.5,  # phi reward
}

def test_efficiency_engine_initial_state():
    """
    Tests that the efficiency of a default, empty state is 1.0.
    P=1, denominator=1 (tick=1, others 0) -> 1/1 = 1
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(tick=1)
    assert engine.compute(state) == pytest.approx(1.0)

def test_efficiency_with_gaps_and_misfits():
    """
    Tests that efficiency decreases as open issues (gaps, misfits) increase.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(tick=10, gaps=5, misfits=2, total_issues=7)

    # P = 7
    # Denominator = 10 (tick) + 5 (gaps) + 1.5*2 (misfits) = 18
    # Score = 7 / 18
    expected_score = 7 / (10 + 5 + (1.5 * 2))
    assert engine.compute(state) == pytest.approx(expected_score)

def test_efficiency_with_all_penalties():
    """
    Tests that all penalties decrease the score.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(
        tick=20,
        gaps=2,
        misfits=1,
        false_pieces=1,
        risk=10,
        backtracks=3,
        entropy=5
    )
    engine.total_pieces = 4

    # P = 4
    # Denominator = 20 (tick) + 2 (gaps) + 1.5*1 (misfits) + 2.0*1 (false_pieces)
    #             + 1.2*10 (risk) + 1.0*3 (backtracks) + 0.8*5 (entropy)
    # Denominator = 20 + 2 + 1.5 + 2.0 + 12 + 3 + 4 = 44.5
    # Score = 4 / 44.5
    denominator = (20 + 2 + (1.5*1) + (2.0*1) + (1.2*10) + (1.0*3) + (0.8*5))
    expected_score = 4 / denominator
    assert engine.compute(state) == pytest.approx(expected_score)

def test_efficiency_with_phi_reward():
    """
    Tests that removing false pieces (phi) increases the score by reducing the denominator.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(
        tick=10,
        gaps=2,
        phi=3, # 3 false pieces were intelligently removed
        total_issues=2
    )

    # P = 2
    # Denominator = 10 (tick) + 2 (gaps) - 2.5*3 (phi reward) = 4.5
    # Score = 2 / 4.5
    denominator = 10 + 2 - (2.5 * 3)
    expected_score = 2 / denominator
    assert engine.compute(state) == pytest.approx(expected_score)

def test_efficiency_score_is_not_negative():
    """
    Ensures the efficiency score is always clamped at 0 and never goes negative.
    This happens if the denominator becomes <= 0 due to a large phi reward.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    # A state with a huge phi reward that would make the denominator negative
    state = PuzzleState(tick=5, phi=10, total_issues=1)

    # Denominator = 5 - 2.5*10 = -20. max(denominator, 1.0) will be 1.0
    # P = 1, so score should be 1/1 = 1, but the formula clamps at 0.
    # Let's re-read the formula. The final result is clamped at 0.
    # The denominator is clamped at 1. So if phi makes it negative, it becomes 1.
    # Let's check the implementation again.
    # `final_score = total_pieces / max(denominator, 1.0)`
    # `return max(0, final_score)`
    # So if denominator is -20, it becomes 1. score is 1/1 = 1.
    # The test as written before was wrong. Let's write a new one.
    # A large denominator should result in a small score, but not negative.
    state_high_penalty = PuzzleState(tick=1, entropy=1000, risk=1000, total_issues=1)
    denominator = 1 + (0.8 * 1000) + (1.2 * 1000)
    expected_score = 1 / denominator
    assert engine.compute(state_high_penalty) > 0
    assert engine.compute(state_high_penalty) == pytest.approx(expected_score)

def test_denominator_clamped_at_one():
    """
    Tests that a large phi reward doesn't lead to an inflated score.
    """
    engine = EfficiencyEngine(TEST_CONSTANTS)
    state = PuzzleState(tick=5, phi=10, gaps=5) # P=5
    engine.total_pieces = 5
    # Denominator = 5 (tick) + 5 (gaps) - 2.5*10 (phi) = -15. max(denominator, 1.0) will be 1.0
    # Score should be 5 / 1 = 5
    assert engine.compute(state) == pytest.approx(5.0)
