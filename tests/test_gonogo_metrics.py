import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service

def test_gonogo_perfect_score():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=100.0,
        correct_responses=14,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=350
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_gonogo_poor_performance():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=40.0,
        correct_responses=6,
        missed_responses=8,
        commission_errors=4,
        reaction_time_ms=700
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 40 * 0.7 = 28
    # commissions: 4 * 15 = 60 penalty -> (100 - 60) * 0.3 = 12
    # expected: 28 + 12 = 40
    assert score == 40

def test_gonogo_zero_input():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=0
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 0.0 -> 0
    # commissions: 0 -> (100 - 0) * 0.3 = 30
    # expected: 30
    assert score == 30

def test_gonogo_omission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=20.0,
        correct_responses=3,
        missed_responses=11,
        commission_errors=0,
        reaction_time_ms=600
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 20 * 0.7 = 14
    # commissions: 0 -> (100 - 0) * 0.3 = 30
    # expected: 44
    assert score == 44

def test_gonogo_commission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=100.0,
        correct_responses=14,
        missed_responses=0,
        commission_errors=8,
        reaction_time_ms=450
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 100 * 0.7 = 70
    # commissions: 8 * 15 = 120 -> max 100 penalty -> (100-100)*0.3 = 0
    # expected: 70
    assert score == 70

def test_gonogo_boundary_minimum():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=14,
        commission_errors=10,
        reaction_time_ms=1200
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_gonogo_boundary_maximum():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=130.0,
        correct_responses=20,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=100
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_gonogo_reaction_time_extremes():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=90.0,
        correct_responses=13,
        missed_responses=1,
        commission_errors=1,
        reaction_time_ms=2500
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 90 * 0.7 = 63
    # commissions: 1 * 15 = 15 penalty -> (100 - 15) * 0.3 = 25.5 -> 25
    # expected: 63 + 25 = 88
    assert score == 88

def test_gonogo_missing_values():
    attempt = TaskAttempt(
        task_id=TaskId.GO_NO_GO,
        domain=CognitiveDomain.COORDINATION,
        accuracy=None,
        correct_responses=None,
        missed_responses=None,
        commission_errors=None,
        reaction_time_ms=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 30
