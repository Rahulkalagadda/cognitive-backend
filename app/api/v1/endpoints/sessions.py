from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.models import AssessmentSession, AssessmentStep
from app.repositories.session import session_repo
from app.schemas.session import (
    SessionStartRequest,
    AssessmentSessionResponse,
    StepResponse,
    TaskAttemptCreate,
    TaskAttemptResponse,
    QuestionnaireResponseCreate,
    QuestionnaireResponseSchema,
    StepStateUpdateRequest,
)
from app.services.session_service import session_service

router = APIRouter()


@router.post("/start", response_model=AssessmentSessionResponse)
async def start_assessment_session(
    request: Request,
    payload: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Initialize a new assessment session or resume an active one using raw link token."""
    ip_address = request.client.host if request.client else None
    session = await session_service.start_session(
        db,
        raw_token=payload.raw_token,
        language=payload.language,
        device_type=payload.device_type,
        user_agent=payload.user_agent,
        ip_address=ip_address,
    )
    # Build response manually to include patient_name (not a DB column, set dynamically)
    return {
        "id": session.id,
        "patient_id": session.patient_id,
        "doctor_id": session.doctor_id,
        "template_id": session.template_id,
        "patient_name": getattr(session, "patient_name", None),
        "status": session.status,
        "language": session.language,
        "current_step_index": session.current_step_index,
        "total_steps": session.total_steps,
        "time_remaining_seconds": session.time_remaining_seconds,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "abandoned_at": session.abandoned_at,
        "device_type": session.device_type,
        "user_agent": session.user_agent,
        "report_id": session.report_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


@router.get("/{id}", response_model=AssessmentSessionResponse)
async def get_session_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Fetch metadata/status for an assessment session."""
    session = await session_repo.get(db, id=id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.get("/{id}/steps", response_model=List[StepResponse])
async def list_session_steps(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List task steps associated with the session."""
    session = await session_repo.get_with_steps(db, session_id=id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Ensure ordered return
    steps = sorted(session.steps, key=lambda s: s.step_index)
    return steps


@router.put("/{id}/step/{step_index}/state", response_model=StepResponse)
async def update_session_step_state(
    id: UUID,
    step_index: int,
    payload: StepStateUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update progress flags for a specific step (e.g. instructions viewed)."""
    step = await session_service.update_step_state(
        db,
        session_id=id,
        step_index=step_index,
        instructions_viewed=payload.instructions_viewed,
        trial_completed=payload.trial_completed,
        is_completed=payload.is_completed,
    )
    return step


@router.post("/{id}/step/{step_index}/attempt", response_model=TaskAttemptResponse)
async def submit_step_attempt(
    id: UUID,
    step_index: int,
    payload: TaskAttemptCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Log an attempt performance (practice or real task) for a session step."""
    ip_address = request.client.host if request.client else None
    attempt = await session_service.record_step_attempt(
        db,
        session_id=id,
        step_index=step_index,
        attempt_in=payload,
        ip_address=ip_address,
    )
    return attempt


@router.post("/{id}/questionnaire", response_model=QuestionnaireResponseSchema)
async def submit_screening_response(
    id: UUID,
    payload: QuestionnaireResponseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Submit a completed screening questionnaire response."""
    ip_address = request.client.host if request.client else None
    response = await session_service.record_questionnaire_response(
        db, session_id=id, obj_in=payload, ip_address=ip_address
    )
    return response


@router.post("/{id}/complete", response_model=AssessmentSessionResponse)
async def complete_assessment_session(
    id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Complete assessment and transition session status."""
    ip_address = request.client.host if request.client else None
    session = await session_service.complete_session(db, session_id=id, ip_address=ip_address)
    return session
