from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class DoctorBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "doctor"
    avatar_url: Optional[str] = None
    license_number: Optional[str] = None
    specialization: Optional[str] = None
    clinic_name: Optional[str] = None
    clinic_city: Optional[str] = None
    is_active: bool = True


class DoctorCreate(DoctorBase):
    password: str


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    license_number: Optional[str] = None
    specialization: Optional[str] = None
    clinic_name: Optional[str] = None
    clinic_city: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class DoctorResponse(DoctorBase):
    id: UUID
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

