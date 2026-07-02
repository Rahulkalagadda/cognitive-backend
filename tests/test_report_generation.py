import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from app.models.models import (
    Report,
    AssessmentSession,
    Patient,
    Doctor,
    TaskAttempt,
)
from app.models.enums import SessionStatus, TaskId, CognitiveDomain
from app.services.report_service import report_service
from app.services.pdf_generator import pdf_generator


@pytest.mark.asyncio
async def test_generate_report_compiles_clinical_metrics(mock_db):
    """Verify that generate_report extracts metrics and adds updating recommendation."""
    session_id = uuid4()
    patient_id = uuid4()
    doctor_id = uuid4()

    # 1. Setup mock session and patient
    mock_patient = Patient(
        id=patient_id,
        name="Alice Smith",
        medical_id="MED-123",
        age=30,
        gender="Female",
        phone="555-0199",
        doctor_id=doctor_id,
    )
    mock_doctor = Doctor(
        id=doctor_id,
        name="Dr. Priya Sharma",
    )

    # Attempts with raw_metrics
    attempts = [
        TaskAttempt(
            task_id=TaskId.CPT,
            domain=CognitiveDomain.ATTENTION,
            is_practice=False,
            accuracy=82.0,
            reaction_time_ms=468,
            correct_responses=15,
            missed_responses=5,
            commission_errors=2,
            raw_metrics={"vigilanceDrop": -12.0},
            computed_score=85,
        ),
        TaskAttempt(
            task_id=TaskId.UPDATING,
            domain=CognitiveDomain.MEMORY,
            is_practice=False,
            accuracy=72.0,
            reaction_time_ms=1200,
            correct_responses=12,
            missed_responses=3,
            commission_errors=0,
            raw_metrics={"updatingEfficiency": 0.58, "difficultyLevel": 3},
            computed_score=72,
        ),
        TaskAttempt(
            task_id=TaskId.TOWER_PUZZLE,
            domain=CognitiveDomain.REASONING,
            is_practice=False,
            accuracy=80.0,
            reaction_time_ms=8400,
            correct_responses=6,
            missed_responses=0,
            commission_errors=0,
            raw_metrics={"efficiencyScore": 0.81, "planningTimeMs": 8400.0},
            computed_score=80,
        ),
        TaskAttempt(
            task_id=TaskId.DIVIDED_ATTENTION,
            domain=CognitiveDomain.ATTENTION,
            is_practice=False,
            accuracy=88.0,
            reaction_time_ms=520,
            correct_responses=25,
            missed_responses=2,
            commission_errors=1,
            raw_metrics={
                "primaryAccuracy": 88.0,
                "secondaryAccuracy": 82.0,
                "interferenceScore": 14.0,
                "dualTaskCostVisual": -12.0,
                "dualTaskCostAuditory": -9.0,
                "rtVariability": 48.0
            },
            computed_score=85,
        ),
    ]

    mock_session = AssessmentSession(
        id=session_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        status=SessionStatus.COMPLETED,
        language="en",
        attempts=attempts,
    )

    # Setup database mocks
    mock_result_session = MagicMock()
    mock_result_session.scalars.return_value.first.return_value = mock_session

    mock_result_doctor = MagicMock()
    mock_result_doctor.scalars.return_value.first.return_value = mock_doctor

    mock_result_q = MagicMock()
    mock_result_q.scalars.return_value.all.return_value = []

    # Mock DB executions
    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "assessment_sessions" in stmt_str:
            return mock_result_session
        elif "doctors" in stmt_str:
            return mock_result_doctor
        elif "questionnaire_responses" in stmt_str:
            return mock_result_q
        return MagicMock()

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    # Mock repository methods
    with patch("app.repositories.patient.patient_repo.get", AsyncMock(return_value=mock_patient)):
        with patch("app.repositories.report.report_repo.get_by_session_id", AsyncMock(return_value=None)):
            # Generate report
            report = await report_service.generate_report(mock_db, session_id=session_id)
                
            # Assertions
            assert report.patient_name == "Alice Smith"
            assert report.clinician_name == "Dr. Priya Sharma"
            
            # Check clinical_metrics compiled dictionary
            c_metrics = report.clinical_metrics
            assert c_metrics is not None
            assert "cpt" in c_metrics
            assert c_metrics["cpt"]["accuracy"] == 82
            assert c_metrics["cpt"]["vigilanceDrop"] == -12.0
            
            assert "updating" in c_metrics
            assert c_metrics["updating"]["updatingEfficiency"] == 0.58
            
            assert "tower-puzzle" in c_metrics
            assert c_metrics["tower-puzzle"]["efficiencyScore"] == 0.81
            assert c_metrics["tower-puzzle"]["planningTimeMs"] == 8400.0
            
            assert "divided-attention" in c_metrics
            assert c_metrics["divided-attention"]["primaryAccuracy"] == 88.0
            assert c_metrics["divided-attention"]["secondaryAccuracy"] == 82.0
            assert c_metrics["divided-attention"]["interferenceScore"] == 14.0
            assert c_metrics["divided-attention"]["dualTaskCostVisual"] == -12.0
            assert c_metrics["divided-attention"]["dualTaskCostAuditory"] == -9.0
            assert c_metrics["divided-attention"]["rtVariability"] == 48.0
            
            # Verify updating recommendation was triggered (updatingEfficiency 0.58 < 0.6)
            assert any("Reduced updating efficiency detected" in rec for rec in report.recommendations)

            # Verify PDF generation works with the clinical_metrics
            pdf_bytes = pdf_generator.generate_report_pdf(report)
            assert len(pdf_bytes) > 0

