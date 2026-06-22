import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service

def test_tower_perfect_score():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=5,
        reaction_time_ms=12000,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_tower_perfect_less_moves():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=4,
        reaction_time_ms=10000,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_tower_one_extra_move():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=6,
        reaction_time_ms=14000,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # move_score: 100 - (1 * 15) = 85
    # time_penalty: 0
    # expected: 85
    assert score == 85

def test_tower_extreme_slow_penalty():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=5,
        reaction_time_ms=25000,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # move_score: 100
    # time_penalty: min(20, (25000 - 15000)/1000) = 10
    # expected: 90
    assert score == 90

def test_tower_maximum_time_penalty():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=5,
        reaction_time_ms=40000,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # move_score: 100
    # time_penalty: min(20, 25) = 20
    # expected: 80
    assert score == 80

def test_tower_many_extra_moves():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=15,
        reaction_time_ms=10000,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # expected: 10
    assert score == 10

def test_tower_zero_input():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=0,
        reaction_time_ms=0,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_tower_missing_optimal_moves_fallback():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=5,
        reaction_time_ms=12000,
        raw_metrics=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_tower_boundary_minimum():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=15,
        reaction_time_ms=30000,
        raw_metrics={"optimalMoves": 5}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # move_score - penalty = 10 - 15 = -5 -> min 0
    assert score == 0

def test_tower_missing_values():
    attempt = TaskAttempt(
        task_id=TaskId.TOWER_PUZZLE,
        domain=CognitiveDomain.REASONING,
        correct_responses=None,
        reaction_time_ms=None,
        raw_metrics=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0
