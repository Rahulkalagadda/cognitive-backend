from uuid import UUID
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.enums import GenderType, ScoreStatus, LanguageCode
from app.schemas.patient import PatientResponse


class ReportGenerateRequest(BaseModel):
    session_id: UUID


class ReportResponse(BaseModel):
    id: UUID
    report_id: str
    medical_id_snapshot: str
    session_id: UUID
    patient_id: UUID
    doctor_id: UUID
    patient_name: str
    patient_age: int
    patient_gender: GenderType
    patient_phone: str
    clinician_name: str
    total_score: int
    score_status: ScoreStatus
    score_attention: Optional[int] = None
    score_memory: Optional[int] = None
    score_reasoning: Optional[int] = None
    score_coordination: Optional[int] = None
    score_perception: Optional[int] = None
    phq9_score: Optional[int] = None
    gad7_score: Optional[int] = None
    pss10_score: Optional[int] = None
    araq_score: Optional[int] = None
    araq_sec_a_score: Optional[int] = None
    araq_sec_b_score: Optional[int] = None
    araq_sec_c_score: Optional[int] = None
    araq_sec_d_score: Optional[int] = None
    recommendations: List[str] = Field(default_factory=list)
    system_version: str
    language: LanguageCode
    is_archived: bool
    clinical_metrics: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScoreHistoryResponse(BaseModel):
    id: UUID
    patient_id: UUID
    report_id: Optional[UUID] = None
    score: int
    attention_score: Optional[int] = None
    memory_score: Optional[int] = None
    reasoning_score: Optional[int] = None
    coordination_score: Optional[int] = None
    perception_score: Optional[int] = None
    label: str
    assessed_on: date
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_patients: int
    scheduled_patients: int
    testing_patients: int
    completed_assessments: int
    recent_patients: List[PatientResponse]
    recent_reports: List[ReportResponse]
