from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class DoctorLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class PatientAccessRequest(BaseModel):
    raw_token: str


class OTPRequest(BaseModel):
    patient_id: UUID
    purpose: str = Field(..., description="Must be one of: email_verify, phone_verify, login")
    channel: str = Field("email", description="Must be one of: email, sms")

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        valid_purposes = {"email_verify", "phone_verify", "login"}
        if v not in valid_purposes:
            raise ValueError(f"purpose must be one of {valid_purposes}")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        valid_channels = {"email", "sms"}
        if v not in valid_channels:
            raise ValueError(f"channel must be one of {valid_channels}")
        return v


class PatientLookupRequest(BaseModel):
    identifier: str = Field(..., description="Patient email address or phone number")


class PatientLookupResponse(BaseModel):
    patient_id: UUID
    name: str
    channel: str = Field(description="Detected channel: 'email' or 'sms'")


class OTPVerify(BaseModel):
    patient_id: UUID
    purpose: str
    otp_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        valid_purposes = {"email_verify", "phone_verify", "login"}
        if v not in valid_purposes:
            raise ValueError(f"purpose must be one of {valid_purposes}")
        return v
