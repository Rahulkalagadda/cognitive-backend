from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_doctor
from app.models.models import AssessmentTemplate, Doctor

router = APIRouter()


@router.get("/")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """List all active assessment battery templates available."""
    stmt = (
        select(AssessmentTemplate)
        .filter(AssessmentTemplate.is_active == True)  # noqa
        .options(selectinload(AssessmentTemplate.tasks))
        .order_by(AssessmentTemplate.name.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{id}")
async def get_template_details(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Retrieve template tasks and duration parameters for a specific test battery."""
    stmt = (
        select(AssessmentTemplate)
        .filter(and_(AssessmentTemplate.id == id, AssessmentTemplate.is_active == True))  # noqa
        .options(selectinload(AssessmentTemplate.tasks))
    )
    result = await db.execute(stmt)
    template = result.scalars().first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment template not found"
        )
    return template
