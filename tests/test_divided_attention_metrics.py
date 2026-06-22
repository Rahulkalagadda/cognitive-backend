"""
Backend scoring tests — Divided Attention (TaskId.DIVIDED_ATTENTION)

Scoring branch (scoring_service.py L94-100):
    raw       = attempt.raw_metrics or {}
    primary   = float(raw.get("primaryAccuracy",   accuracy))
    secondary = float(raw.get("secondaryAccuracy", accuracy))
    computed_score = int((primary + secondary) / 2)

Primary task  = tracking dot on grid (spatial attention)
Secondary task = detecting red flashes (vigilance)

Score = average of both task accuracies, clamped to [0, 100].
"""

import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service


def test_divided_attention_perfect_both():
    """Both primary and secondary at 100% → score = 100"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=100.0,
        correct_responses=30,
        missed_responses=0,
        commission_errors=0,
        raw_metrics={"primaryAccuracy": 100.0, "secondaryAccuracy": 100.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # (100 + 100) / 2 = 100
    assert score == 100


def test_divided_attention_typical():
    """Typical dual-task performance: primary strong, secondary moderate"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=82.0,
        correct_responses=24,
        missed_responses=4,
        commission_errors=2,
        raw_metrics={"primaryAccuracy": 80.0, "secondaryAccuracy": 70.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # (80 + 70) / 2 = 75
    assert score == 75


def test_divided_attention_primary_fails():
    """Primary tracking fails completely, secondary is fine"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=50.0,
        correct_responses=12,
        missed_responses=12,
        commission_errors=0,
        raw_metrics={"primaryAccuracy": 0.0, "secondaryAccuracy": 100.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # (0 + 100) / 2 = 50
    assert score == 50


def test_divided_attention_secondary_fails():
    """Primary tracking perfect, secondary (red detection) fails"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=50.0,
        correct_responses=12,
        missed_responses=12,
        commission_errors=0,
        raw_metrics={"primaryAccuracy": 100.0, "secondaryAccuracy": 0.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # (100 + 0) / 2 = 50
    assert score == 50


def test_divided_attention_fallback_to_accuracy():
    """No raw_metrics → falls back to overall accuracy for both tasks"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=60.0,
        correct_responses=15,
        missed_responses=10,
        commission_errors=0,
        raw_metrics=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # raw = {}, primary = accuracy = 60, secondary = accuracy = 60
    # (60 + 60) / 2 = 60
    assert score == 60


def test_divided_attention_partial_raw_metrics():
    """Only primaryAccuracy in raw_metrics → secondaryAccuracy falls back to accuracy"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=70.0,
        correct_responses=18,
        missed_responses=6,
        commission_errors=0,
        raw_metrics={"primaryAccuracy": 90.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # primary = 90, secondary = accuracy = 70
    # (90 + 70) / 2 = 80
    assert score == 80


def test_divided_attention_poor_performance():
    """Both tasks low → low clinical score"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=20.0,
        correct_responses=5,
        missed_responses=20,
        commission_errors=5,
        raw_metrics={"primaryAccuracy": 20.0, "secondaryAccuracy": 10.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # (20 + 10) / 2 = 15
    assert score == 15


def test_divided_attention_zero_input():
    """All zeroes → score = 0"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=0,
        commission_errors=0,
        raw_metrics={"primaryAccuracy": 0.0, "secondaryAccuracy": 0.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # (0 + 0) / 2 = 0
    assert score == 0


def test_divided_attention_boundary_maximum():
    """Overflow values capped at 100"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=120.0,
        correct_responses=30,
        missed_responses=0,
        commission_errors=0,
        raw_metrics={"primaryAccuracy": 120.0, "secondaryAccuracy": 110.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # (120 + 110) / 2 = 115 → capped to 100
    assert score == 100


def test_divided_attention_missing_values():
    """None accuracy + None raw_metrics → both fallback to 0"""
    attempt = TaskAttempt(
        task_id=TaskId.DIVIDED_ATTENTION,
        domain=CognitiveDomain.ATTENTION,
        accuracy=None,
        correct_responses=None,
        missed_responses=None,
        commission_errors=None,
        raw_metrics=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy=0, raw={}, primary=0, secondary=0 → (0+0)/2 = 0
    assert score == 0
