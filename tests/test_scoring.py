import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service


def test_scoring_cpt():
    """Verify CPT attention scoring weights accuracy, omissions, and commissions."""
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=90.0,
        correct_responses=18,
        missed_responses=2,      # 2 omissions -> 20 penalty
        commission_errors=1,     # 1 commission -> 10 penalty
        reaction_time_ms=450,
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy weight: 90 * 0.6 = 54
    # commissions: (100 - 10) * 0.2 = 18
    # omissions: (100 - 20) * 0.2 = 16
    # Total expected: 54 + 18 + 16 = 88
    assert score == 88


def test_scoring_word_recall():
    """Verify Word Recall memory scoring calculates correct/total recall percentage."""
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=75.0,
        correct_responses=6,
        missed_responses=2,
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 6 correct out of 8 total = 75% -> 75
    assert score == 75


def test_scoring_tower_puzzle():
    """Verify Tower Puzzle reasoning scoring applies move penalties and response time thresholds."""
    # Scenario A: Optimal moves (5) with fast execution
    attempt_optimal = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=5,  # moves taken
        reaction_time_ms=12000,  # 12 seconds (under 15s threshold)
        raw_metrics={"optimalMoves": 5},
    )
    score_optimal = scoring_service.calculate_attempt_score(attempt_optimal)
    assert score_optimal == 100

    # Scenario B: Extra moves penalty
    attempt_penalty = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=7,  # 2 extra moves -> 30 penalty
        reaction_time_ms=10000,
        raw_metrics={"optimalMoves": 5},
    )
    score_penalty = scoring_service.calculate_attempt_score(attempt_penalty)
    # 100 - (2 * 15) = 70
    assert score_penalty == 70


def test_scoring_go_no_go():
    """Verify Go/No-Go coordination scoring penalises commission errors."""
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=80.0,
        commission_errors=2,  # 2 commissions -> 30 penalty
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy weight: 80 * 0.7 = 56
    # commissions weight: (100 - 30) * 0.3 = 21
    # Total expected: 56 + 21 = 77
    assert score == 77
