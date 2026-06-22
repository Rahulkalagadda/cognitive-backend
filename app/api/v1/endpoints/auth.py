from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_doctor
from app.models.models import Doctor, Report
from app.schemas.doctor import DoctorResponse
from app.schemas.auth import Token, PatientAccessRequest, OTPRequest, OTPVerify, PatientLookupRequest, PatientLookupResponse
from app.schemas.patient import PatientResponse
from app.schemas.report import ReportResponse
from app.services.auth_service import auth_service
from app.repositories.patient import patient_repo

router = APIRouter()


@router.get("/me", response_model=DoctorResponse)
async def get_current_doctor_profile(
    current_doctor: Doctor = Depends(get_current_doctor),
) -> Any:
    """Retrieve details of the authenticated doctor."""
    return current_doctor


@router.post("/login", response_model=Token)
async def login_doctor(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """OAuth2 compatible token login for Doctors, returning JWT access token."""
    ip_address = request.client.host if request.client else None
    doctor, token = await auth_service.authenticate_doctor(
        db, email=form_data.username, password=form_data.password, ip_address=ip_address
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/patient/validate", response_model=PatientResponse)
async def validate_patient_link(
    request: Request,
    payload: PatientAccessRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Validate raw patient assessment URL token."""
    ip_address = request.client.host if request.client else None
    patient = await auth_service.authenticate_patient_token(
        db, raw_token=payload.raw_token, ip_address=ip_address
    )
    return patient


@router.post("/patient/lookup", response_model=PatientLookupResponse)
async def lookup_patient_by_identifier(
    request: Request,
    payload: PatientLookupRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Find a patient by email or phone number to initiate OTP login flow."""
    import re
    from sqlalchemy import func, or_
    from app.models.models import Patient

    identifier = payload.identifier.strip()
    is_phone = re.match(r"^[0-9]{10,15}$", identifier.replace(" ", "").replace("-", ""))

    stmt = select(Patient).where(
        or_(
            func.lower(Patient.email) == identifier.lower(),
            Patient.phone == identifier.replace(" ", "").replace("-", "")
        )
    )
    result = await db.execute(stmt)
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email or phone number."
        )

    channel = "sms" if is_phone else "email"
    return PatientLookupResponse(
        patient_id=patient.id,
        name=patient.name,
        channel=channel
    )


@router.post("/otp/request")
async def request_otp(
    request: Request,
    payload: OTPRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Generate and request a new verification OTP for a patient."""
    ip_address = request.client.host if request.client else None
    verification, code = await auth_service.create_otp_code(
        db,
        patient_id=payload.patient_id,
        purpose=payload.purpose,
        channel=payload.channel,
        ip_address=ip_address,
    )
    return {
        "msg": "OTP generated successfully",
        "verification_id": verification.id,
        "expires_at": verification.expires_at,
        "code_simulation": code,  # Included in sandbox mode for verification simplicity
    }


@router.post("/otp/verify")
async def verify_otp(
    request: Request,
    payload: OTPVerify,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Verify submitted 6-digit OTP code."""
    ip_address = request.client.host if request.client else None
    success = await auth_service.verify_otp_code(
        db,
        patient_id=payload.patient_id,
        purpose=payload.purpose,
        otp_code=payload.otp_code,
        ip_address=ip_address,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed: Incorrect code."
        )
    return {"msg": "Verification successful", "verified": True}


# ─── Patient Self-Service Endpoints ──────────────────────────────────────────
# These endpoints are authenticated only by patient_id (set client-side after
# successful OTP verification). No doctor JWT is required.

class PatientProfilePublic(PatientResponse):
    """Extends PatientResponse with the assigned doctor's display name."""
    doctor_name: str = "Clinician"


@router.get("/patient/{patient_id}/profile", response_model=PatientProfilePublic)
async def get_patient_own_profile(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return a patient's own profile + assigned doctor name.
    Called from the patient portal after OTP login. No doctor JWT required.
    """
    patient = await patient_repo.get(db, id=patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Fetch assigned doctor's display name
    doctor_stmt = select(Doctor).filter(Doctor.id == patient.doctor_id)
    doctor = (await db.execute(doctor_stmt)).scalars().first()
    doctor_name = f"Dr. {doctor.name}" if doctor else "Your Clinician"

    data = PatientProfilePublic.model_validate(patient, from_attributes=True)
    data.doctor_name = doctor_name
    return data


@router.get("/patient/{patient_id}/reports", response_model=List[ReportResponse])
async def get_patient_own_reports(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return all reports belonging to a patient.
    Called from the patient portal after OTP login. No doctor JWT required.
    """
    patient = await patient_repo.get(db, id=patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    reports_stmt = (
        select(Report)
        .filter(Report.patient_id == patient_id, Report.is_archived == False)  # noqa
        .order_by(Report.created_at.desc())
    )
    reports = list((await db.execute(reports_stmt)).scalars().all())
    return reports
