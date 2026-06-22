import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.exceptions import AuthException, BadRequestException, NotFoundException
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_assessment_token_hash,
    generate_otp_code,
    get_otp_hash,
)
from app.models.models import Doctor, Patient, OTPVerification, AuditLog
from app.models.enums import AuditActorType, AuditAction
from app.repositories.doctor import doctor_repo
from app.repositories.patient import patient_repo

logger = logging.getLogger(__name__)


class AuthService:
    async def authenticate_doctor(
        self, db: AsyncSession, email: str, password: str, ip_address: Optional[str] = None
    ) -> Tuple[Doctor, str]:
        """Authenticate a doctor by email and password, returning the Doctor object and JWT token."""
        doctor = await doctor_repo.get_by_email(db, email=email)
        if not doctor or not doctor.is_active:
            # Audit log login failure (doctor not found or inactive)
            await self._log_audit(
                db,
                actor_id=None,
                actor_type=AuditActorType.SYSTEM,
                action=AuditAction.LOGIN,
                entity_type="doctor",
                entity_id=None,
                metadata={"email": email, "success": False, "reason": "invalid_credentials_or_inactive"},
                ip_address=ip_address,
            )
            raise AuthException("Invalid email or password")

        if not verify_password(password, doctor.password_hash):
            # Audit log login failure
            await self._log_audit(
                db,
                actor_id=doctor.id,
                actor_type=AuditActorType.DOCTOR,
                action=AuditAction.LOGIN,
                entity_type="doctor",
                entity_id=doctor.id,
                metadata={"email": email, "success": False, "reason": "incorrect_password"},
                ip_address=ip_address,
            )
            raise AuthException("Invalid email or password")

        # Update last login timestamp
        doctor.last_login_at = datetime.now(timezone.utc)
        db.add(doctor)

        # Generate access token
        token = create_access_token(subject=doctor.id)

        # Audit log successful login
        await self._log_audit(
            db,
            actor_id=doctor.id,
            actor_type=AuditActorType.DOCTOR,
            action=AuditAction.LOGIN,
            entity_type="doctor",
            entity_id=doctor.id,
            metadata={"email": email, "success": True},
            ip_address=ip_address,
        )

        return doctor, token

    async def authenticate_patient_token(
        self, db: AsyncSession, raw_token: str, ip_address: Optional[str] = None
    ) -> Patient:
        """Authenticate a patient using the raw assessment token in the URL."""
        token_hash = get_assessment_token_hash(raw_token)
        patient = await patient_repo.get_by_token_hash(db, token_hash=token_hash)
        
        if not patient:
            raise AuthException("Invalid assessment token link")

        if patient.assessment_token_used:
            raise AuthException("This assessment link has already been used")

        if patient.assessment_token_expires_at:
            # Explicit timezone aware check
            now_tz = datetime.now(timezone.utc)
            if patient.assessment_token_expires_at < now_tz:
                raise AuthException("This assessment link has expired")

        # Log patient authentication audit event
        await self._log_audit(
            db,
            actor_id=patient.id,
            actor_type=AuditActorType.PATIENT,
            action=AuditAction.LOGIN,
            entity_type="patient",
            entity_id=patient.id,
            metadata={"success": True, "token_auth": True},
            ip_address=ip_address,
        )

        return patient

    async def create_otp_code(
        self, db: AsyncSession, patient_id: UUID, purpose: str, channel: str, ip_address: Optional[str] = None
    ) -> Tuple[OTPVerification, str]:
        """Generate and save a hashed OTP, returning the verification record and plain code."""
        patient = await patient_repo.get(db, patient_id)
        if not patient:
            raise NotFoundException("Patient not found")

        # Generate random 6 digit code
        otp_code = generate_otp_code()
        otp_hash = get_otp_hash(otp_code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        otp_verification = OTPVerification(
            patient_id=patient_id,
            otp_code_hash=otp_hash,
            purpose=purpose,
            channel=channel,
            expires_at=expires_at,
            verified=False,
            attempts=0,
            ip_address=ip_address,
        )
        db.add(otp_verification)
        await db.flush()

        # Print OTP to logs (sandbox mode simulation)
        logger.info(f"Sandbox Simulation: OTP code '{otp_code}' generated for Patient {patient.name} ({channel}: {patient.email if channel == 'email' else patient.phone})")

        # Audit log OTP request
        await self._log_audit(
            db,
            actor_id=patient_id,
            actor_type=AuditActorType.PATIENT,
            action=AuditAction.OTP_REQUEST,
            entity_type="patient",
            entity_id=patient_id,
            metadata={"purpose": purpose, "channel": channel},
            ip_address=ip_address,
        )

        return otp_verification, otp_code

    async def verify_otp_code(
        self, db: AsyncSession, patient_id: UUID, purpose: str, otp_code: str, ip_address: Optional[str] = None
    ) -> bool:
        """Verify the OTP code, marking verified status in otp_verifications and patient records."""
        patient = await patient_repo.get(db, patient_id)
        if not patient:
            raise NotFoundException("Patient not found")

        # Get latest active unverified verification record
        stmt = (
            select(OTPVerification)
            .filter(
                and_(
                    OTPVerification.patient_id == patient_id,
                    OTPVerification.purpose == purpose,
                    OTPVerification.verified == False,  # noqa
                )
            )
            .order_by(desc(OTPVerification.created_at))
            .limit(1)
        )
        result = await db.execute(stmt)
        otp_record = result.scalars().first()

        if not otp_record:
            raise BadRequestException("No active OTP request found for this patient and purpose")

        # Check expiration
        now_tz = datetime.now(timezone.utc)
        if otp_record.expires_at < now_tz:
            raise BadRequestException("OTP has expired. Please request a new one.")

        # Check attempt lockout
        if otp_record.attempts >= 5:
            raise BadRequestException("Maximum validation attempts exceeded. Please request a new OTP.")

        # Increment attempts
        otp_record.attempts += 1
        db.add(otp_record)

        # Hash provided code and compare
        provided_hash = get_otp_hash(otp_code)
        if provided_hash != otp_record.otp_code_hash:
            # Audit log incorrect code submission
            await self._log_audit(
                db,
                actor_id=patient_id,
                actor_type=AuditActorType.PATIENT,
                action=AuditAction.OTP_VERIFY,
                entity_type="patient",
                entity_id=patient_id,
                metadata={"purpose": purpose, "success": False, "reason": "incorrect_code"},
                ip_address=ip_address,
            )
            return False

        # Code matched successfully
        otp_record.verified = True
        otp_record.verified_at = datetime.now(timezone.utc)
        db.add(otp_record)

        # Update verified status on Patient model
        patient.otp_verified_at = datetime.now(timezone.utc)
        if purpose == "email_verify" or purpose == "login":
            patient.email_verified = True
        elif purpose == "phone_verify":
            patient.phone_verified = True

        db.add(patient)

        # Audit log successful verification
        await self._log_audit(
            db,
            actor_id=patient_id,
            actor_type=AuditActorType.PATIENT,
            action=AuditAction.OTP_VERIFY,
            entity_type="patient",
            entity_id=patient_id,
            metadata={"purpose": purpose, "success": True},
            ip_address=ip_address,
        )

        return True

    async def _log_audit(
        self,
        db: AsyncSession,
        actor_id: Optional[UUID],
        actor_type: AuditActorType,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[UUID],
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ):
        """Append-only audit logger helper."""
        audit = AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata,
            ip_address=ip_address,
        )
        db.add(audit)
        # Flush to allow database validation triggers to execute (e.g. validate_audit_actor)
        await db.flush()


auth_service = AuthService()
