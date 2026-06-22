from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import CRUDBase
from app.models.models import Patient
from app.models.enums import PatientStatus


class CRUDPatient(CRUDBase[Patient]):
    async def get_by_medical_id_and_doctor(
        self, db: AsyncSession, *, doctor_id: UUID, medical_id: str
    ) -> Optional[Patient]:
        result = await db.execute(
            select(self.model).filter(
                and_(
                    self.model.doctor_id == doctor_id,
                    self.model.medical_id == medical_id,
                )
            )
        )
        return result.scalars().first()

    async def get_by_token_hash(
        self, db: AsyncSession, *, token_hash: str
    ) -> Optional[Patient]:
        result = await db.execute(
            select(self.model).filter(self.model.assessment_token_hash == token_hash)
        )
        return result.scalars().first()

    async def list_by_doctor(
        self,
        db: AsyncSession,
        *,
        doctor_id: UUID,
        skip: int = 0,
        limit: int = 100,
        search_query: Optional[str] = None,
        status: Optional[PatientStatus] = None,
    ) -> List[Patient]:
        stmt = select(self.model).filter(self.model.doctor_id == doctor_id)
        
        if status:
            stmt = stmt.filter(self.model.status == status)
            
        if search_query:
            search_query_lower = f"%{search_query.strip().lower()}%"
            stmt = stmt.filter(
                or_(
                    func.lower(self.model.name).like(search_query_lower),
                    func.lower(self.model.medical_id).like(search_query_lower),
                    func.lower(self.model.email).like(search_query_lower),
                )
            )
            
        stmt = stmt.order_by(self.model.name.asc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


patient_repo = CRUDPatient(Patient)
