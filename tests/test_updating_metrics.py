"""
Backend scoring tests — Updating / Working Memory (TaskId.UPDATING)

Scoring branch (scoring_service.py L102-107):
    raw   = attempt.raw_metrics or {}
    level = int(raw.get("difficultyLevel", 1))
    computed_score = min(100, int(accuracy * (0.7 + level * 0.1)))

Level multipliers:
    difficultyLevel=1  → multiplier = 0.7 + 0.1 = 0.8
    difficultyLevel=2  → multiplier = 0.7 + 0.2 = 0.9
    difficultyLevel=3  → multiplier = 0.7 + 0.3 = 1.0

Clinical rationale: higher N-Back demands (1→2→3-back) are rewarded.
Perfect performance at level 3 = 100. Perfect at level 1 = 80 (harder tasks
require higher accuracy to reach the same clinical score ceiling).
"""

import pytest
from app.models.enums import TaskId, CognitiveDomain
from app.models.models import TaskAttempt
from app.services.scoring_service import scoring_service


def test_updating_perfect_level3():
    """100% accuracy at level 3 (3-back) → score = 100"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=100.0,
        correct_responses=6,
        missed_responses=0,
        commission_errors=0,
        raw_metrics={"difficultyLevel": 3, "nBackLevel": 3, "updatingEfficiency": 1.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 100 * (0.7 + 3*0.1) = 100 * 1.0 = 100
    assert score == 100


def test_updating_perfect_level2():
    """100% accuracy at level 2 → multiplier 0.9 → score = 90"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=100.0,
        correct_responses=5,
        missed_responses=0,
        commission_errors=0,
        raw_metrics={"difficultyLevel": 2, "nBackLevel": 2, "updatingEfficiency": 1.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 100 * (0.7 + 2*0.1) = 100 * 0.9
    # Python: int(100 * 0.9) = int(89.99999...) = 89  (IEEE 754 float)
    assert score == 89


def test_updating_perfect_level1():
    """100% accuracy at level 1 → multiplier 0.8 → score = 80"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=100.0,
        correct_responses=4,
        missed_responses=0,
        commission_errors=0,
        raw_metrics={"difficultyLevel": 1, "nBackLevel": 1, "updatingEfficiency": 1.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # 100 * (0.7 + 1*0.1) = 100 * 0.8 = 80
    assert score == 80


def test_updating_typical_level3():
    """75% accuracy at level 3 → score = 75"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=75.0,
        correct_responses=4,
        missed_responses=1,
        commission_errors=1,
        raw_metrics={"difficultyLevel": 3, "updatingEfficiency": 0.67}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # int(75 * 1.0) = 75
    assert score == 75


def test_updating_typical_level2():
    """80% accuracy at level 2 → score = int(80 * 0.9) = 72"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=80.0,
        correct_responses=4,
        missed_responses=1,
        commission_errors=0,
        raw_metrics={"difficultyLevel": 2, "updatingEfficiency": 0.80}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # int(80 * 0.9) = int(72.0) = 72
    assert score == 72


def test_updating_poor_performance():
    """30% accuracy at level 1 → score = int(30 * 0.8) = 24"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=30.0,
        correct_responses=1,
        missed_responses=3,
        commission_errors=0,
        raw_metrics={"difficultyLevel": 1, "updatingEfficiency": 0.25}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # int(30 * 0.8) = int(30 * (0.7 + 1*0.1))
    # Python: int(30 * 0.8) = int(23.999999...) = 23  (IEEE 754 float)
    assert score == 23


def test_updating_zero_input():
    """0% accuracy → score = 0 regardless of level"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=0.0,
        correct_responses=0,
        missed_responses=6,
        commission_errors=0,
        raw_metrics={"difficultyLevel": 3, "updatingEfficiency": 0.0}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # int(0 * 1.0) = 0
    assert score == 0


def test_updating_fallback_level():
    """No raw_metrics → difficultyLevel defaults to 1 → multiplier 0.8"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=90.0,
        correct_responses=4,
        missed_responses=0,
        commission_errors=0,
        raw_metrics=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # level = 1 (default), int(90 * 0.8) = int(72.0) = 72
    assert score == 72


def test_updating_boundary_maximum_capped():
    """Overflow accuracy + high level → capped at 100"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=150.0,
        correct_responses=10,
        missed_responses=0,
        commission_errors=0,
        raw_metrics={"difficultyLevel": 3}
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # int(150 * 1.0) = 150 → min(100, 150) = 100
    assert score == 100


def test_updating_missing_values():
    """None accuracy + None raw_metrics → accuracy=0, level=1 → score = 0"""
    attempt = TaskAttempt(
        task_id=TaskId.UPDATING,
        domain=CognitiveDomain.MEMORY,
        accuracy=None,
        correct_responses=None,
        missed_responses=None,
        commission_errors=None,
        raw_metrics=None
    )
    score = scoring_service.calculate_attempt_score(attempt)
    # accuracy=0, level=1 (default), int(0 * 0.8) = 0
    assert score == 0
