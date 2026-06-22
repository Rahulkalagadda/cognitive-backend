from uuid import UUID
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.enums import GenderType, PatientStatus


class PatientBase(BaseModel):
    name: str
    email: EmailStr
    age: int = Field(..., gt=0, lt=130)
    gender: GenderType
    phone: str = Field(..., description="Phone number containing 10-15 digits")
    status: PatientStatus = PatientStatus.SCHEDULED
    medical_id: str = Field(..., description="Alphanumeric plus dashes only")
    notes: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Enforce Postgres CHECK (phone ~ '^[0-9]{10,15}$')
        import re
        if not re.match(r"^[0-9]{10,15}$", v):
            raise ValueError("Phone number must contain only digits (10 to 15 characters).")
        return v

    @field_validator("medical_id")
    @classmethod
    def validate_medical_id(cls, v: str) -> str:
        # Enforce Postgres CHECK (medical_id ~ '^[A-Za-z0-9\-]+$')
        import re
        if not re.match(r"^[A-Za-z0-9\-]+$", v):
            raise ValueError("Medical ID must be alphanumeric or contain dashes only.")
        return v


class PatientCreate(PatientBase):
    template_id: Optional[UUID] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, gt=0, lt=130)
    gender: Optional[GenderType] = None
    phone: Optional[str] = None
    status: Optional[PatientStatus] = None
    medical_id: Optional[str] = None
    notes: Optional[str] = None
    template_id: Optional[UUID] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re
        if not re.match(r"^[0-9]{10,15}$", v):
            raise ValueError("Phone number must contain only digits (10 to 15 characters).")
        return v

    @field_validator("medical_id")
    @classmethod
    def validate_medical_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re
        if not re.match(r"^[A-Za-z0-9\-]+$", v):
            raise ValueError("Medical ID must be alphanumeric or contain dashes only.")
        return v


class PatientResponse(PatientBase):
    id: UUID
    doctor_id: UUID
    template_id: Optional[UUID] = None
    assessment_token_used: bool
    assessment_token_expires_at: Optional[datetime] = None
    last_assessment_date: Optional[date] = None
    email_verified: bool
    phone_verified: bool
    otp_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    raw_assessment_link: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            date: lambda d: d.isoformat()
        }
