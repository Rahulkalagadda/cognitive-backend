import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service

def test_cpt_perfect_score():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=100.0,
        correct_responses=20,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=300
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_cpt_poor_performance():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=20.0,
        correct_responses=4,
        missed_responses=16,
        commission_errors=8,
        reaction_time_ms=800
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 20 * 0.6 = 12
    # commissions: 8 * 10 = 80 penalty -> (100 - 80) * 0.2 = 4
    # omissions: 16 * 10 = 160 penalty -> max 100 -> (100 - 100) * 0.2 = 0
    # expected: 12 + 4 = 16
    assert score == 16

def test_cpt_zero_input():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=0
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 0
    # commissions: 0 -> (100 - 0) * 0.2 = 20
    # omissions: 0 -> (100 - 0) * 0.2 = 20
    # expected: 40
    assert score == 40

def test_cpt_omission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=10.0,
        correct_responses=2,
        missed_responses=18,
        commission_errors=0,
        reaction_time_ms=500
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 10 * 0.6 = 6
    # commissions: 0 -> (100 - 0) * 0.2 = 20
    # omissions: 18 -> max 100 penalty -> 0
    # expected: 26
    assert score == 26

def test_cpt_commission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=100.0,
        correct_responses=20,
        missed_responses=0,
        commission_errors=15,
        reaction_time_ms=400
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 100 * 0.6 = 60
    # commissions: 15 -> max 100 penalty -> 0
    # omissions: 0 -> (100-0)*0.2 = 20
    # expected: 80
    assert score == 80

def test_cpt_boundary_minimum():
    # Force everything to be worst case to test min 0
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=20,
        commission_errors=20,
        reaction_time_ms=1000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_cpt_boundary_maximum():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=150.0, # theoretical overflow
        correct_responses=30,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=100
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_cpt_reaction_time_extreme_fast():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=95.0,
        correct_responses=19,
        missed_responses=1,
        commission_errors=1,
        reaction_time_ms=50
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy: 95 * 0.6 = 57
    # commissions: 1 -> 10 penalty -> (100 - 10) * 0.2 = 18
    # omissions: 1 -> 10 penalty -> (100 - 10) * 0.2 = 18
    # expected: 57 + 18 + 18 = 93
    assert score == 93

def test_cpt_reaction_time_extreme_slow():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=95.0,
        correct_responses=19,
        missed_responses=1,
        commission_errors=1,
        reaction_time_ms=3000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 93

def test_cpt_missing_values():
    attempt = TaskAttempt(
        task_id=TaskId.CPT,
        domain=CognitiveDomain.ATTENTION,
        accuracy=None,
        correct_responses=None,
        missed_responses=None,
        commission_errors=None,
        reaction_time_ms=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 40
