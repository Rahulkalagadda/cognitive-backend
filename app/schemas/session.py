from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator
from app.models.enums import TaskId, CognitiveDomain, SessionStatus, LanguageCode, QuestionnaireSlug


class SessionStartRequest(BaseModel):
    raw_token: str
    language: LanguageCode = LanguageCode.EN
    device_type: Optional[str] = None
    user_agent: Optional[str] = None


class AssessmentSessionResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    template_id: Optional[UUID] = None
    patient_name: Optional[str] = None  # Denormalized for frontend convenience
    status: SessionStatus
    language: LanguageCode
    current_step_index: int
    total_steps: int
    time_remaining_seconds: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    abandoned_at: Optional[datetime] = None
    device_type: Optional[str] = None
    user_agent: Optional[str] = None
    report_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StepResponse(BaseModel):
    id: UUID
    session_id: UUID
    template_task_id: Optional[UUID] = None
    step_index: int
    domain: CognitiveDomain
    task_id: TaskId
    title: str
    instructions: Optional[str] = None
    duration_seconds: int
    config: Optional[dict] = None
    instructions_viewed: bool
    instructions_viewed_at: Optional[datetime] = None
    trial_completed: bool
    trial_completed_at: Optional[datetime] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskAttemptCreate(BaseModel):
    task_id: TaskId
    domain: CognitiveDomain
    is_practice: bool = False
    accuracy: Optional[float] = Field(None, ge=0.0, le=100.0)
    reaction_time_ms: Optional[int] = Field(None, ge=0)
    correct_responses: int = Field(0, ge=0)
    missed_responses: int = Field(0, ge=0)
    commission_errors: int = Field(0, ge=0)
    completion_time_s: Optional[float] = Field(None, ge=0.0)
    raw_metrics: Optional[dict] = None
    computed_score: Optional[int] = Field(None, ge=0, le=100)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskAttemptResponse(TaskAttemptCreate):
    id: UUID
    session_id: UUID
    step_id: UUID
    patient_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionnaireResponseCreate(BaseModel):
    slug: QuestionnaireSlug
    language: LanguageCode = LanguageCode.EN
    answers: dict = Field(..., description="Must be a non-empty dictionary object")
    total_score: int = Field(0, ge=0)
    item_count: int = Field(..., ge=1)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, v: dict) -> dict:
        # Enforce Postgres CHECK (jsonb_typeof(answers) = 'object' AND answers <> '{}'::jsonb)
        if not isinstance(v, dict):
            raise ValueError("answers must be an object (dict)")
        if not v:
            raise ValueError("answers cannot be an empty object")
        return v


class QuestionnaireResponseSchema(QuestionnaireResponseCreate):
    id: UUID
    session_id: UUID
    patient_id: UUID
    completed_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StepStateUpdateRequest(BaseModel):
    instructions_viewed: Optional[bool] = None
    trial_completed: Optional[bool] = None
    is_completed: Optional[bool] = None
