import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.security import generate_raw_token, get_assessment_token_hash
from app.models.models import Patient, AssessmentTemplate, AuditLog
from app.models.enums import AuditActorType, AuditAction
from app.repositories.patient import patient_repo
from app.schemas.patient import PatientCreate, PatientUpdate

logger = logging.getLogger(__name__)


class PatientService:
    async def create_patient(
        self, db: AsyncSession, *, doctor_id: UUID, obj_in: PatientCreate, ip_address: Optional[str] = None
    ) -> Tuple[Patient, str]:
        """Create a new patient record, unique check, and generate secure URL token."""
        # 1. Enforce unique medical ID scoped to doctor
        existing_medical = await patient_repo.get_by_medical_id_and_doctor(
            db, doctor_id=doctor_id, medical_id=obj_in.medical_id
        )
        if existing_medical:
            raise BadRequestException(
                f"A patient with Medical ID '{obj_in.medical_id}' already exists under your account."
            )

        # 2. Check email uniqueness scoped to doctor
        email_clean = obj_in.email.strip().lower()
        stmt = select(Patient).filter(
            and_(Patient.doctor_id == doctor_id, func.lower(Patient.email) == email_clean)
        )
        existing_email = (await db.execute(stmt)).scalars().first()
        if existing_email:
            raise BadRequestException(
                f"A patient with email '{obj_in.email}' already exists under your account."
            )

        # 3. Associate default template if not specified
        template_id = obj_in.template_id
        if not template_id:
            tpl_stmt = select(AssessmentTemplate).filter(
                and_(AssessmentTemplate.is_default == True, AssessmentTemplate.is_active == True)  # noqa
            )
            default_tpl = (await db.execute(tpl_stmt)).scalars().first()
            if default_tpl:
                template_id = default_tpl.id

        # 4. Generate URL assessment token and hash it
        raw_token = generate_raw_token()
        token_hash = get_assessment_token_hash(raw_token)
        # Default assessment link valid for 30 days
        token_expires = datetime.now(timezone.utc) + timedelta(days=30)

        # 5. Populate model details
        patient_data = obj_in.model_dump()
        patient_data["doctor_id"] = doctor_id
        patient_data["template_id"] = template_id
        patient_data["assessment_token_hash"] = token_hash
        patient_data["assessment_token_expires_at"] = token_expires
        patient_data["assessment_token_used"] = False

        db_patient = Patient(**patient_data)
        db.add(db_patient)
        await db.flush()

        # Audit log creation
        audit = AuditLog(
            actor_id=doctor_id,
            actor_type=AuditActorType.DOCTOR,
            action=AuditAction.PATIENT_CREATE,
            entity_type="patient",
            entity_id=db_patient.id,
            metadata={"medical_id": db_patient.medical_id},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        return db_patient, raw_token

    async def update_patient(
        self, db: AsyncSession, *, doctor_id: UUID, patient_id: UUID, obj_in: PatientUpdate, ip_address: Optional[str] = None
    ) -> Patient:
        """Update a patient profile (doctor scoped verification)."""
        patient = await patient_repo.get(db, patient_id)
        if not patient or patient.doctor_id != doctor_id:
            raise NotFoundException("Patient not found or access denied")

        # Check unique medical ID constraints if changed
        if obj_in.medical_id and obj_in.medical_id != patient.medical_id:
            existing = await patient_repo.get_by_medical_id_and_doctor(
                db, doctor_id=doctor_id, medical_id=obj_in.medical_id
            )
            if existing:
                raise BadRequestException(f"Medical ID '{obj_in.medical_id}' is already assigned to another patient.")

        updated_patient = await patient_repo.update(db, db_obj=patient, obj_in=obj_in)

        # Audit log patient update
        audit = AuditLog(
            actor_id=doctor_id,
            actor_type=AuditActorType.DOCTOR,
            action=AuditAction.PATIENT_UPDATE,
            entity_type="patient",
            entity_id=patient.id,
            metadata={"changed_fields": list(obj_in.model_dump(exclude_unset=True).keys())},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        return updated_patient

    async def delete_patient(
        self, db: AsyncSession, *, doctor_id: UUID, patient_id: UUID, ip_address: Optional[str] = None
    ) -> Patient:
        """Hard delete a patient record."""
        patient = await patient_repo.get(db, patient_id)
        if not patient or patient.doctor_id != doctor_id:
            raise NotFoundException("Patient not found or access denied")

        await patient_repo.remove(db, id=patient_id)

        # Audit log patient delete
        audit = AuditLog(
            actor_id=doctor_id,
            actor_type=AuditActorType.DOCTOR,
            action=AuditAction.PATIENT_DELETE,
            entity_type="patient",
            entity_id=patient_id,
            metadata={"name": patient.name, "medical_id": patient.medical_id},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        return patient




patient_service = PatientService()
