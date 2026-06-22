import uuid
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Date, Numeric, ForeignKey, text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.schema import FetchedValue

from app.db.base_class import Base
from app.models.enums import (
    GenderType,
    PatientStatus,
    CognitiveDomain,
    TaskId,
    SessionStatus,
    QuestionnaireSlug,
    ScoreStatus,
    LanguageCode,
    AuditActorType,
    AuditAction,
    OtpPurpose,
    OtpChannel,
)

def get_values(enum_class):
    return [e.value for e in enum_class]


class SystemMetadata(Base):
    __tablename__ = "system_metadata"
    __table_args__ = {"extend_existing": True}

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AssessmentTemplate(Base):
    __tablename__ = "assessment_templates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator: Mapped[Optional["Doctor"]] = relationship("Doctor", foreign_keys=[created_by])
    tasks: Mapped[List["TemplateTask"]] = relationship("TemplateTask", back_populates="template", cascade="all, delete-orphan")


class TemplateTask(Base):
    __tablename__ = "template_tasks"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_templates.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[TaskId] = mapped_column(SQLEnum(TaskId, native_enum=True, name="task_id", values_callable=get_values), nullable=False)
    domain: Mapped[CognitiveDomain] = mapped_column(SQLEnum(CognitiveDomain, native_enum=True, name="cognitive_domain", values_callable=get_values), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)  # SMALLINT in SQL
    title: Mapped[str] = mapped_column(String, nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    template: Mapped["AssessmentTemplate"] = relationship("AssessmentTemplate", back_populates="tasks")


class Doctor(Base):
    __tablename__ = "doctors"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="doctor")
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    clinic_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    clinic_city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    patients: Mapped[List["Patient"]] = relationship("Patient", back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_templates.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)  # SMALLINT in SQL
    gender: Mapped[GenderType] = mapped_column(SQLEnum(GenderType, native_enum=True, name="gender_type", values_callable=get_values), nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PatientStatus] = mapped_column(SQLEnum(PatientStatus, native_enum=True, name="patient_status", values_callable=get_values), nullable=False, default=PatientStatus.SCHEDULED)
    medical_id: Mapped[str] = mapped_column(String, nullable=False)
    assessment_token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    assessment_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assessment_token_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_assessment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    otp_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="patients")
    template: Mapped[Optional["AssessmentTemplate"]] = relationship("AssessmentTemplate")
    score_history: Mapped[List["PatientScoreHistory"]] = relationship("PatientScoreHistory", back_populates="patient", cascade="all, delete-orphan")
    sessions: Mapped[List["AssessmentSession"]] = relationship("AssessmentSession", back_populates="patient", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="patient")


class OTPVerification(Base):
    __tablename__ = "otp_verifications"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    otp_code_hash: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(SQLEnum(OtpPurpose, native_enum=True, name="otp_purpose", values_callable=get_values), nullable=False)
    channel: Mapped[OtpChannel] = mapped_column(SQLEnum(OtpChannel, native_enum=True, name="otp_channel", values_callable=get_values), nullable=False, default=OtpChannel.EMAIL)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # SMALLINT
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PatientScoreHistory(Base):
    __tablename__ = "patient_score_history"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # SMALLINT
    attention_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reasoning_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    coordination_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perception_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    assessed_on: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="score_history")
    report: Mapped[Optional["Report"]] = relationship("Report", back_populates="score_history")


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_templates.id", ondelete="SET NULL"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus, native_enum=True, name="session_status", values_callable=get_values), nullable=False, default=SessionStatus.INITIALIZED)
    language: Mapped[LanguageCode] = mapped_column(SQLEnum(LanguageCode, native_enum=True, name="language_code", values_callable=get_values), nullable=False, default=LanguageCode.EN)
    current_step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    time_remaining_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="sessions")
    steps: Mapped[List["AssessmentStep"]] = relationship("AssessmentStep", back_populates="session", cascade="all, delete-orphan")
    attempts: Mapped[List["TaskAttempt"]] = relationship("TaskAttempt", back_populates="session", cascade="all, delete-orphan")
    report: Mapped[Optional["Report"]] = relationship("Report", back_populates="session", uselist=False, lazy="joined")

    @property
    def report_id(self) -> Optional[uuid.UUID]:
        if "report" in self.__dict__:
            return self.report.id if self.report else None
        return None


class AssessmentStep(Base):
    __tablename__ = "assessment_steps"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False
    )
    template_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("template_tasks.id", ondelete="SET NULL"), nullable=True
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    domain: Mapped[CognitiveDomain] = mapped_column(SQLEnum(CognitiveDomain, native_enum=True, name="cognitive_domain", values_callable=get_values), nullable=False)
    task_id: Mapped[TaskId] = mapped_column(SQLEnum(TaskId, native_enum=True, name="task_id", values_callable=get_values), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    instructions_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    instructions_viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trial_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    session: Mapped["AssessmentSession"] = relationship("AssessmentSession", back_populates="steps")
    attempts: Mapped[List["TaskAttempt"]] = relationship("TaskAttempt", back_populates="step", cascade="all, delete-orphan")


class QuestionnaireResponse(Base):
    __tablename__ = "questionnaire_responses"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[QuestionnaireSlug] = mapped_column(SQLEnum(QuestionnaireSlug, native_enum=True, name="questionnaire_slug", values_callable=get_values), nullable=False)
    language: Mapped[LanguageCode] = mapped_column(SQLEnum(LanguageCode, native_enum=True, name="language_code", values_callable=get_values), nullable=False, default=LanguageCode.EN)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TaskAttempt(Base):
    __tablename__ = "task_attempts"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_steps.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[TaskId] = mapped_column(SQLEnum(TaskId, native_enum=True, name="task_id", values_callable=get_values), nullable=False)
    domain: Mapped[CognitiveDomain] = mapped_column(SQLEnum(CognitiveDomain, native_enum=True, name="cognitive_domain", values_callable=get_values), nullable=False)
    is_practice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accuracy: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    reaction_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    correct_responses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missed_responses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    commission_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_time_s: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    raw_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    computed_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    session: Mapped["AssessmentSession"] = relationship("AssessmentSession", back_populates="attempts")
    step: Mapped["AssessmentStep"] = relationship("AssessmentStep", back_populates="attempts")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    medical_id_snapshot: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_sessions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    patient_name: Mapped[str] = mapped_column(String, nullable=False)
    patient_age: Mapped[int] = mapped_column(Integer, nullable=False)
    patient_gender: Mapped[GenderType] = mapped_column(SQLEnum(GenderType, native_enum=True, name="gender_type", values_callable=get_values), nullable=False)
    patient_phone: Mapped[str] = mapped_column(String, nullable=False)
    clinician_name: Mapped[str] = mapped_column(String, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Generated always as stored on Postgres database level: CAP total_score thresholds mapping.
    # To prevent SQLAlchemy trying to insert or update this field, mark as FetchedValue.
    score_status: Mapped[ScoreStatus] = mapped_column(
        SQLEnum(ScoreStatus, native_enum=True, name="score_status", values_callable=get_values), nullable=False, server_default=FetchedValue()
    )

    score_attention: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_memory: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_reasoning: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_coordination: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_perception: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    phq9_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gad7_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pss10_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendations: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, server_default=text("'{}'"))
    system_version: Mapped[str] = mapped_column(String, nullable=False, default="2.5.0-LTS")
    language: Mapped[LanguageCode] = mapped_column(SQLEnum(LanguageCode, native_enum=True, name="language_code", values_callable=get_values), nullable=False, default=LanguageCode.EN)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clinical_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    session: Mapped["AssessmentSession"] = relationship("AssessmentSession", back_populates="report")
    patient: Mapped["Patient"] = relationship("Patient", back_populates="reports")
    score_history: Mapped[List["PatientScoreHistory"]] = relationship("PatientScoreHistory", back_populates="report")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_type: Mapped[AuditActorType] = mapped_column(SQLEnum(AuditActorType, native_enum=True, name="audit_actor_type", values_callable=get_values), nullable=False, default=AuditActorType.SYSTEM)
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction, native_enum=True, name="audit_action", values_callable=get_values), nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
