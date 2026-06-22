from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import CRUDBase
from app.models.models import Report, Patient, AssessmentSession, PatientScoreHistory
from app.models.enums import PatientStatus, SessionStatus
from app.core.security import get_assessment_token_hash


class CRUDReport(CRUDBase[Report]):
    async def get_by_session_id(self, db: AsyncSession, *, session_id: UUID) -> Optional[Report]:
        result = await db.execute(
            select(self.model).filter(self.model.session_id == session_id)
        )
        return result.scalars().first()

    async def get_by_session_token_hash(
        self, db: AsyncSession, *, raw_token: str
    ) -> Optional[Report]:
        """Look up a report via the session's stored token_hash.
        Works even after the patient's assessment_token_used flag is True.
        """
        token_hash = get_assessment_token_hash(raw_token)
        session_stmt = select(AssessmentSession).filter(
            AssessmentSession.token_hash == token_hash
        )
        session = (await db.execute(session_stmt)).scalars().first()
        if not session:
            return None
        report_stmt = select(self.model).filter(self.model.session_id == session.id)
        return (await db.execute(report_stmt)).scalars().first()

    async def list_by_doctor(
        self,
        db: AsyncSession,
        *,
        doctor_id: UUID,
        skip: int = 0,
        limit: int = 100,
        search_query: Optional[str] = None,
    ) -> List[Report]:
        stmt = select(self.model).filter(
            and_(self.model.doctor_id == doctor_id, self.model.is_archived == False)  # noqa
        )
        
        if search_query:
            search_query_lower = f"%{search_query.strip().lower()}%"
            stmt = stmt.filter(
                func.lower(self.model.patient_name).like(search_query_lower)
            )
            
        stmt = stmt.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_patient_score_history(
        self, db: AsyncSession, *, patient_id: UUID
    ) -> List[PatientScoreHistory]:
        stmt = (
            select(PatientScoreHistory)
            .filter(PatientScoreHistory.patient_id == patient_id)
            .order_by(PatientScoreHistory.assessed_on.asc(), PatientScoreHistory.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_dashboard_summary(
        self, db: AsyncSession, *, doctor_id: UUID
    ) -> dict:
        # 1. Total patients
        total_p_stmt = select(func.count(Patient.id)).filter(Patient.doctor_id == doctor_id)
        total_p = (await db.execute(total_p_stmt)).scalar() or 0

        # 2. Scheduled patients
        scheduled_p_stmt = select(func.count(Patient.id)).filter(
            and_(Patient.doctor_id == doctor_id, Patient.status == PatientStatus.SCHEDULED)
        )
        scheduled_p = (await db.execute(scheduled_p_stmt)).scalar() or 0

        # 3. Testing patients
        testing_p_stmt = select(func.count(Patient.id)).filter(
            and_(Patient.doctor_id == doctor_id, Patient.status == PatientStatus.TESTING)
        )
        testing_p = (await db.execute(testing_p_stmt)).scalar() or 0

        # 4. Completed assessments (total completed sessions)
        completed_sessions_stmt = select(func.count(AssessmentSession.id)).filter(
            and_(
                AssessmentSession.doctor_id == doctor_id,
                AssessmentSession.status == SessionStatus.COMPLETED,
            )
        )
        completed_sessions = (await db.execute(completed_sessions_stmt)).scalar() or 0

        return {
            "total_patients": total_p,
            "scheduled_patients": scheduled_p,
            "testing_patients": testing_p,
            "completed_assessments": completed_sessions,
        }


report_repo = CRUDReport(Report)
