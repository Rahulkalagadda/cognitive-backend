import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service

def test_nback_perfect_score():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=100.0,
        correct_responses=6,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=400
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_nback_poor_performance():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=30.0,
        correct_responses=2,
        missed_responses=4,
        commission_errors=3,
        reaction_time_ms=900
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 30

def test_nback_zero_input():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=0
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_nback_omission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=16.67,
        correct_responses=1,
        missed_responses=5,
        commission_errors=0,
        reaction_time_ms=500
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 16

def test_nback_commission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=83.33,
        correct_responses=5,
        missed_responses=1,
        commission_errors=10,
        reaction_time_ms=450
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 83

def test_nback_boundary_minimum():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=-10.0,
        correct_responses=0,
        missed_responses=6,
        commission_errors=10,
        reaction_time_ms=1000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_nback_boundary_maximum():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=150.0,
        correct_responses=10,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=200
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_nback_reaction_time_extremes():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=90.0,
        correct_responses=9,
        missed_responses=1,
        commission_errors=0,
        reaction_time_ms=4000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 90

def test_nback_missing_values():
    attempt = TaskAttempt(
        task_id=TaskId.N_BACK,
        domain=CognitiveDomain.MEMORY,
        accuracy=None,
        correct_responses=None,
        missed_responses=None,
        commission_errors=None,
        reaction_time_ms=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0
