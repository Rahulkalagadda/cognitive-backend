import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.security import get_assessment_token_hash
from app.models.models import (
    Patient,
    AssessmentTemplate,
    TemplateTask,
    AssessmentSession,
    AssessmentStep,
    TaskAttempt,
    QuestionnaireResponse,
    AuditLog,
)
from app.models.enums import SessionStatus, AuditActorType, AuditAction
from app.repositories.session import session_repo
from app.repositories.patient import patient_repo
from app.services.auth_service import auth_service
from app.services.scoring_service import scoring_service
from app.schemas.session import TaskAttemptCreate, QuestionnaireResponseCreate

logger = logging.getLogger(__name__)


class SessionService:
    async def start_session(
        self,
        db: AsyncSession,
        *,
        raw_token: str,
        language: str = "en",
        device_type: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AssessmentSession:
        """Start an assessment session from the patient URL token."""
        from app.core.security import get_assessment_token_hash

        token_hash = get_assessment_token_hash(raw_token)

        # 1. Check for an existing active session by token hash (resume path).
        #    This must happen BEFORE authenticate_patient_token because the token
        #    is marked used=True once a session starts — resuming would otherwise 401.
        existing_session = await session_repo.get_active_session_by_token_hash(db, token_hash=token_hash)
        if existing_session:
            patient = await patient_repo.get(db, existing_session.patient_id)
            logger.info(f"Resuming active session {existing_session.id} for Patient {patient.name if patient else 'unknown'}")
            existing_session.patient_name = patient.name if patient else "Patient"  # type: ignore[attr-defined]
            return existing_session

        # 2. Fresh session — authenticate patient (validates token not used/expired)
        patient = await auth_service.authenticate_patient_token(db, raw_token=raw_token, ip_address=ip_address)

        # 3. Retrieve assessment template tasks
        template_id = patient.template_id
        if not template_id:
            tpl_stmt = select(AssessmentTemplate).filter(
                and_(AssessmentTemplate.is_default == True, AssessmentTemplate.is_active == True)  # noqa
            )
            default_tpl = (await db.execute(tpl_stmt)).scalars().first()
            if not default_tpl:
                raise BadRequestException("No default active assessment template found.")
            template_id = default_tpl.id

        # Get template tasks
        tasks_stmt = (
            select(TemplateTask)
            .filter(and_(TemplateTask.template_id == template_id, TemplateTask.is_active == True))  # noqa
            .order_by(TemplateTask.step_order.asc())
        )
        tasks = list((await db.execute(tasks_stmt)).scalars().all())
        if not tasks:
            raise BadRequestException("The assigned template contains no active tasks.")

        # 4. Initialize session (session.doctor_id is set securely from patient)
        session_token_hash = get_assessment_token_hash(raw_token)
        session = AssessmentSession(
            patient_id=patient.id,
            doctor_id=patient.doctor_id,
            template_id=template_id,
            token_hash=session_token_hash,
            status=SessionStatus.STARTED,
            language=language,
            current_step_index=0,
            total_steps=len(tasks),
            started_at=datetime.now(timezone.utc),
            device_type=device_type,
            user_agent=user_agent,
        )
        db.add(session)
        await db.flush()

        # 5. Build session steps from template tasks
        for idx, task in enumerate(tasks):
            step = AssessmentStep(
                session_id=session.id,
                template_task_id=task.id,
                step_index=idx,
                domain=task.domain,
                task_id=task.task_id,
                title=task.title,
                instructions=task.instructions,
                duration_seconds=task.duration_seconds,
                config=task.config,
                instructions_viewed=False,
                trial_completed=False,
                is_completed=False,
            )
            db.add(step)

        # 6. Mark patient's URL token as used
        patient.assessment_token_used = True
        patient.status = "Testing"
        db.add(patient)

        # 7. Audit log session start
        audit = AuditLog(
            actor_id=patient.id,
            actor_type=AuditActorType.PATIENT,
            action=AuditAction.SESSION_START,
            entity_type="session",
            entity_id=session.id,
            metadata={"template_id": str(template_id)},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        # Attach patient name for the response (not persisted, only for serialization)
        session.patient_name = patient.name  # type: ignore[attr-defined]

        return session

    async def record_step_attempt(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        step_index: int,
        attempt_in: TaskAttemptCreate,
        ip_address: Optional[str] = None,
    ) -> TaskAttempt:
        """Record a practice trial or a real task attempt for the given step index."""
        # Retrieve session
        session = await session_repo.get(db, session_id)
        if not session:
            raise NotFoundException("Session not found")
        if session.status in {SessionStatus.COMPLETED, SessionStatus.ABANDONED}:
            raise BadRequestException("Cannot add attempts to a completed or abandoned session")

        # Find corresponding step
        step_stmt = select(AssessmentStep).filter(
            and_(AssessmentStep.session_id == session_id, AssessmentStep.step_index == step_index)
        )
        step = (await db.execute(step_stmt)).scalars().first()
        if not step:
            raise NotFoundException(f"Step with index {step_index} not found in session")

        if not attempt_in.is_practice and step.is_completed:
            raise BadRequestException("Real attempt already recorded for this step")

        # Instantiate attempt
        attempt = TaskAttempt(
            session=session,
            step=step,
            patient_id=session.patient_id,
            task_id=step.task_id,
            domain=step.domain,
            is_practice=attempt_in.is_practice,
            accuracy=attempt_in.accuracy,
            reaction_time_ms=attempt_in.reaction_time_ms,
            correct_responses=attempt_in.correct_responses,
            missed_responses=attempt_in.missed_responses,
            commission_errors=attempt_in.commission_errors,
            completion_time_s=attempt_in.completion_time_s,
            raw_metrics=attempt_in.raw_metrics,
            started_at=attempt_in.started_at or datetime.now(timezone.utc),
            completed_at=attempt_in.completed_at or datetime.now(timezone.utc),
        )

        # Compute performance score using scoring service
        attempt.computed_score = scoring_service.calculate_attempt_score(attempt)
        db.add(attempt)
        await db.flush()

        # Update step state
        if attempt_in.is_practice:
            step.trial_completed = True
            step.trial_completed_at = datetime.now(timezone.utc)
            db.add(step)
        else:
            step.is_completed = True
            step.completed_at = datetime.now(timezone.utc)
            db.add(step)

            # Advance current step index pointer on session
            session.current_step_index = step_index + 1
            if session.current_step_index >= session.total_steps:
                # Last step completed; automatically mark session as completed
                session.status = SessionStatus.COMPLETED
                session.completed_at = datetime.now(timezone.utc)
                
                # Update patient status back to stable
                patient = await patient_repo.get(db, session.patient_id)
                if patient:
                    patient.status = "Stable"
                    patient.last_assessment_date = datetime.now(timezone.utc).date()
                    db.add(patient)
                
                # Generate the report automatically!
                from app.services.report_service import report_service
                await report_service.generate_report(db, session_id=session.id, ip_address=ip_address)

            db.add(session)

        # Audit log task submission
        audit = AuditLog(
            actor_id=session.patient_id,
            actor_type=AuditActorType.PATIENT,
            action=AuditAction.TASK_SUBMIT,
            entity_type="task_attempt",
            entity_id=attempt.id,
            metadata={"task_id": step.task_id, "is_practice": attempt_in.is_practice, "score": attempt.computed_score},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        return attempt

    async def record_questionnaire_response(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        obj_in: QuestionnaireResponseCreate,
        ip_address: Optional[str] = None,
    ) -> QuestionnaireResponse:
        """Submit screening questionnaire response."""
        session = await session_repo.get(db, session_id)
        if not session:
            raise NotFoundException("Session not found")

        # Unique constraint check (one of each slug per session)
        q_stmt = select(QuestionnaireResponse).filter(
            and_(QuestionnaireResponse.session_id == session_id, QuestionnaireResponse.slug == obj_in.slug)
        )
        existing = (await db.execute(q_stmt)).scalars().first()
        if existing:
            raise BadRequestException(f"Questionnaire response '{obj_in.slug}' already submitted for this session")

        # Create response
        q_response = QuestionnaireResponse(
            session_id=session_id,
            patient_id=session.patient_id,
            slug=obj_in.slug,
            language=obj_in.language,
            answers=obj_in.answers,
            total_score=obj_in.total_score,
            item_count=obj_in.item_count,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(q_response)
        await db.flush()

        # Audit log questionnaire submission
        audit = AuditLog(
            actor_id=session.patient_id,
            actor_type=AuditActorType.PATIENT,
            action=AuditAction.QUESTIONNAIRE_SUBMIT,
            entity_type="questionnaire_response",
            entity_id=q_response.id,
            metadata={"slug": obj_in.slug, "score": obj_in.total_score},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        return q_response

    async def complete_session(
        self, db: AsyncSession, *, session_id: UUID, ip_address: Optional[str] = None
    ) -> AssessmentSession:
        """Transition session status to completed manually."""
        session = await session_repo.get(db, session_id)
        if not session:
            raise NotFoundException("Session not found")

        if session.status == SessionStatus.COMPLETED:
            return session

        # Transition status
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        db.add(session)

        # Update patient status back to stable
        patient = await patient_repo.get(db, session.patient_id)
        if patient:
            patient.status = "Stable"
            patient.last_assessment_date = datetime.now(timezone.utc).date()
            db.add(patient)

        # Generate the report automatically!
        from app.services.report_service import report_service
        await report_service.generate_report(db, session_id=session_id, ip_address=ip_address)

        # Audit log session complete
        audit = AuditLog(
            actor_id=session.patient_id,
            actor_type=AuditActorType.PATIENT,
            action=AuditAction.SESSION_COMPLETE,
            entity_type="session",
            entity_id=session_id,
            metadata={"current_step": session.current_step_index, "total_steps": session.total_steps},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        return session

    async def update_step_state(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        step_index: int,
        instructions_viewed: Optional[bool] = None,
        trial_completed: Optional[bool] = None,
        is_completed: Optional[bool] = None,
    ) -> AssessmentStep:
        """Update step progress flags (e.g. instructions viewed)."""
        step_stmt = select(AssessmentStep).filter(
            and_(AssessmentStep.session_id == session_id, AssessmentStep.step_index == step_index)
        )
        step = (await db.execute(step_stmt)).scalars().first()
        if not step:
            raise NotFoundException("Step not found")

        if instructions_viewed is not None:
            step.instructions_viewed = instructions_viewed
            if instructions_viewed:
                step.instructions_viewed_at = datetime.now(timezone.utc)
        
        if trial_completed is not None:
            step.trial_completed = trial_completed
            if trial_completed:
                step.trial_completed_at = datetime.now(timezone.utc)

        if is_completed is not None:
            step.is_completed = is_completed
            if is_completed:
                step.completed_at = datetime.now(timezone.utc)

        db.add(step)
        await db.flush()
        return step


session_service = SessionService()
