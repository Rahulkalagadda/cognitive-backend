import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service

def test_shape_match_perfect_score():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=100.0,
        correct_responses=10,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=1500
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_shape_match_perfect_score_fast_bonus():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=90.0,
        correct_responses=9,
        missed_responses=1,
        commission_errors=0,
        reaction_time_ms=1000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_shape_match_poor_performance():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=40.0,
        correct_responses=4,
        missed_responses=0,
        commission_errors=6,
        reaction_time_ms=1800
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 40

def test_shape_match_poor_performance_slow_penalty():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=50.0,
        correct_responses=5,
        missed_responses=0,
        commission_errors=5,
        reaction_time_ms=3000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 50 - 15 = 35
    assert score == 35

def test_shape_match_zero_input():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=0
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_shape_match_omission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=10.0,
        correct_responses=1,
        missed_responses=9,
        commission_errors=0,
        reaction_time_ms=2000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 10

def test_shape_match_commission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=10,
        reaction_time_ms=1500
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_shape_match_boundary_minimum():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=5.0,
        correct_responses=0,
        missed_responses=10,
        commission_errors=0,
        reaction_time_ms=3000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_shape_match_boundary_maximum():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=100.0,
        correct_responses=10,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=800
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_shape_match_missing_values():
    attempt = TaskAttempt(
        task_id=TaskId.SHAPE_MATCH,
        domain=CognitiveDomain.PERCEPTION,
        accuracy=None,
        correct_responses=None,
        missed_responses=None,
        commission_errors=None,
        reaction_time_ms=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0
