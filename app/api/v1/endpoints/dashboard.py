from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_db, get_current_doctor
from app.models.models import Doctor, Patient, Report
from app.repositories.report import report_repo
from app.schemas.patient import PatientResponse
from app.schemas.report import ReportResponse

router = APIRouter()


@router.get("/stats")
async def get_stats_summary(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Get aggregated stats dashboard count numbers for the clinician home screen."""
    stats = await report_repo.get_dashboard_summary(db, doctor_id=current_doctor.id)
    return stats


@router.get("/recent-patients", response_model=List[PatientResponse])
async def get_recent_patients(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Fetch the 5 most recently updated or registered patients."""
    stmt = (
        select(Patient)
        .filter(Patient.doctor_id == current_doctor.id)
        .order_by(desc(Patient.updated_at))
        .limit(5)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/recent-reports", response_model=List[ReportResponse])
async def get_recent_reports(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Fetch the 5 most recently compiled patient reports."""
    stmt = (
        select(Report)
        .filter(Report.doctor_id == current_doctor.id)
        .order_by(desc(Report.created_at))
        .limit(5)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
