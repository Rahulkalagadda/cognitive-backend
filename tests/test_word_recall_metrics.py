import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service

def test_word_recall_perfect_score():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=100.0,
        correct_responses=8,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=2000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_word_recall_poor_performance():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=25.0,
        correct_responses=2,
        missed_responses=6,
        commission_errors=4,
        reaction_time_ms=4000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # correct = 2, missed = 6 -> total = 8. score = 2 / 8 = 25%
    assert score == 25

def test_word_recall_zero_input():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=0
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_word_recall_zero_input_accuracy_fallback():
    # If correct + missed is 0, falls back to accuracy
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=50.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=2,
        reaction_time_ms=5000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 50

def test_word_recall_omission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=12.5,
        correct_responses=1,
        missed_responses=7,
        commission_errors=0,
        reaction_time_ms=3000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 1/8 = 12.5% -> 12
    assert score == 12

def test_word_recall_commission_heavy():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=75.0,
        correct_responses=6,
        missed_responses=2,
        commission_errors=15,
        reaction_time_ms=4000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 6 correct, 2 missed -> total = 8. 6/8 = 75%
    assert score == 75

def test_word_recall_boundary_minimum():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=-10.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=1000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0

def test_word_recall_boundary_maximum():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=130.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        reaction_time_ms=1000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 100

def test_word_recall_reaction_time_extremes():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=87.5,
        correct_responses=7,
        missed_responses=1,
        commission_errors=1,
        reaction_time_ms=25000
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 7/8 = 87.5% -> 87
    assert score == 87

def test_word_recall_missing_values():
    attempt = TaskAttempt(
        task_id=TaskId.WORD_RECALL,
        domain=CognitiveDomain.MEMORY,
        accuracy=None,
        correct_responses=None,
        missed_responses=None,
        commission_errors=None,
        reaction_time_ms=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    assert score == 0
