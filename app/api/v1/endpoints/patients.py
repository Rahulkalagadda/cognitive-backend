from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_doctor
from app.models.models import Doctor
from app.repositories.patient import patient_repo
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.services.patient_service import patient_service

router = APIRouter()


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
) -> Any:
    """List patients registered under the authenticated doctor's account."""
    patients = await patient_repo.list_by_doctor(
        db,
        doctor_id=current_doctor.id,
        skip=skip,
        limit=limit,
        search_query=search,
        status=status,
    )
    return patients


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    request: Request,
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Create a new patient record and generate an assessment access link."""
    ip_address = request.client.host if request.client else None
    patient, raw_token = await patient_service.create_patient(
        db, doctor_id=current_doctor.id, obj_in=payload, ip_address=ip_address
    )
    
    # Construct complete link for patient assessment start
    # Can reside on local 3000 port by default or be loaded dynamically
    frontend_host = request.headers.get("referer") or "http://localhost:3000"
    from urllib.parse import urlparse
    parsed = urlparse(frontend_host)
    frontend_host = f"{parsed.scheme}://{parsed.netloc}"

    raw_assessment_link = f"{frontend_host}/assessment/{raw_token}"
    
    # Map to schema output model
    response_data = PatientResponse.from_orm(patient)
    response_data.raw_assessment_link = raw_assessment_link
    return response_data


@router.get("/{id}", response_model=PatientResponse)
async def get_patient_profile(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Fetch profile details for a specific patient (access restricted to owning doctor)."""
    from fastapi import HTTPException
    patient = await patient_repo.get(db, id=id)
    if not patient or patient.doctor_id != current_doctor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or access denied"
        )
    return patient


@router.put("/{id}", response_model=PatientResponse)
async def update_patient_profile(
    id: UUID,
    payload: PatientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Update patient demographic details."""
    ip_address = request.client.host if request.client else None
    patient = await patient_service.update_patient(
        db, doctor_id=current_doctor.id, patient_id=id, obj_in=payload, ip_address=ip_address
    )
    return patient


@router.delete("/{id}", response_model=PatientResponse)
async def delete_patient_record(
    id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Hard delete patient and cascade clear dependent sessions/attempts."""
    ip_address = request.client.host if request.client else None
    patient = await patient_service.delete_patient(
        db, doctor_id=current_doctor.id, patient_id=id, ip_address=ip_address
    )
    return patient


@router.post("/{id}/regenerate-link", response_model=PatientResponse)
async def regenerate_assessment_link(
    id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """
    Generate a fresh assessment access link for an existing patient.
    Resets the used flag, creates a new token with a 30-day expiry,
    and returns the full assessment URL in raw_assessment_link.
    The previous link is immediately invalidated.
    """
    from datetime import datetime, timedelta, timezone
    from app.core.security import generate_raw_token, get_assessment_token_hash

    patient = await patient_repo.get(db, id=id)
    if not patient or patient.doctor_id != current_doctor.id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or access denied"
        )

    # Generate fresh token
    raw_token = generate_raw_token()
    token_hash = get_assessment_token_hash(raw_token)
    token_expires = datetime.now(timezone.utc) + timedelta(days=30)

    patient.assessment_token_hash = token_hash
    patient.assessment_token_expires_at = token_expires
    patient.assessment_token_used = False
    await db.flush()
    # Refresh is required: flush() expires ORM attributes in async context,
    # which would cause a MissingGreenlet error when Pydantic serializes the model.
    await db.refresh(patient)

    # Build the full assessment link
    frontend_host = request.headers.get("referer") or "http://localhost:3000"
    from urllib.parse import urlparse
    parsed = urlparse(frontend_host)
    frontend_host = f"{parsed.scheme}://{parsed.netloc}"
    raw_assessment_link = f"{frontend_host}/assessment/{raw_token}"

    response_data = PatientResponse.from_orm(patient)
    response_data.raw_assessment_link = raw_assessment_link
    return response_data

